"""Agent 1: News Researcher.

Fetches top 10 technology news stories per category using DuckDuckGo,
scrapes snippets, deduplicates, and enforces research guardrails.
"""

from __future__ import annotations
from utils.datetime import utcnow

import asyncio
from datetime import datetime
from typing import Any, Optional

from agents.base import BaseAgent
from config import CONFIG
from integrations.web_search import WebSearchClient
from models.news import NewsArticle, NewsBatch
from utils.text_utils import count_words, enforce_word_limit
from utils.logger import get_logger

log = get_logger("researcher")

RESEARCHER_SYSTEM = """You are Agent 1 — News Researcher. Your job is to fetch technology news and produce factual, concise summaries.

RULES:
- Only consider news published in the last 7 days.
- Do NOT fabricate URLs or sources — every article must link to a real domain.
- Title: max {title_max} words. Description: max {desc_max} words.
- Extract factual key points only; never invent claims.
- No clickbait, no conspiracy content.
- Source diversity: no more than 2 articles from the same domain.
- Category must be from the allowed list: {categories}.

Return JSON: {{"articles": [{{"title": "...", "description": "...", "source": "...", "url": "...", "published_time": "ISO", "category": "..."}}]}}.
"""


class NewsResearcherAgent(BaseAgent):
    name = "Agent 1: News Researcher"
    description = "Fetches top 10 technology news stories and produces factual summaries."
    allowed_tools = ["web_search", "optimize_tokens"]

    def __init__(self, llm=None, token_manager=None, search_client: Optional[WebSearchClient] = None) -> None:
        super().__init__(llm=llm, token_manager=token_manager)
        self.search = search_client or WebSearchClient()

    async def execute(self, input_data: dict) -> dict:
        categories = input_data.get("categories") or CONFIG.pipeline_categories
        session_id = input_data.get("session_id", "default")
        max_per_cat = input_data.get("max_per_category", 5)

        articles: list[NewsArticle] = []
        seen_domains: dict[str, int] = {}
        seen_urls: set[str] = set()

        for category in categories:
            results = await self.search.search(f"{category} technology news", max_results=max(max_per_cat, 6))
            for r in results:
                url = r.href
                if url in seen_urls:
                    continue
                from urllib.parse import urlparse

                domain = urlparse(url).netloc.lower()
                if seen_domains.get(domain, 0) >= 2:
                    continue
                seen_domains[domain] = seen_domains.get(domain, 0) + 1
                seen_urls.add(url)

                snippet = r.body or await self.search.scrape_summary(url, max_chars=800)
                article = NewsArticle(
                    title=enforce_word_limit(r.title[:200], CONFIG.title_max_words, "title"),
                    description=enforce_word_limit(snippet, CONFIG.desc_max_words, "description"),
                    source=domain,
                    url=url,
                    published_time=utcnow(),
                    category=category,
                    session_id=session_id,
                )
                articles.append(article)

            if len(articles) >= 10:
                break

        articles = articles[:10]

        system_prompt = RESEARCHER_SYSTEM.format(
            title_max=CONFIG.title_max_words,
            desc_max=CONFIG.desc_max_words,
            categories=", ".join(CONFIG.pipeline_categories),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Refine these news summaries into factual JSON. Articles: {len(articles)}"},
        ]
        if self.llm is not None and self.token_manager is not None:
            await self.llm_call(messages)

        batch = NewsBatch(session_id=session_id, articles=articles, category=input_data.get("category"))
        log.info("research_complete", articles=len(articles), categories=categories)
        return {"news_batch": batch.model_dump(), "articles": [a.model_dump() for a in articles]}

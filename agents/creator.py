"""Agent 2: Content Creator.

Creates platform-specific social media content (Instagram, LinkedIn, Twitter)
from news articles, including image prompts.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from agents.base import BaseAgent
from config import CONFIG
from models.content import SocialContent, PostVariant, PlatformType
from models.news import NewsBatch
from utils.text_utils import count_words
from utils.logger import get_logger

log = get_logger("creator")

CREATOR_SYSTEM = """You are Agent 2 — Content Creator. Transform news articles into engaging social media posts.

RULES:
- Select the 3-5 most shareable stories based on engagement potential.
- Instagram: detailed image prompt (for FLUX/DALL-E) + caption (max 2200 chars, ≤150 words body). Use emojis sparingly.
- LinkedIn: professional post (max 300 words) with ≤5 hashtags. Minimal emojis.
- Twitter: thread of 3-4 tweets (each ≤280 chars) or single post ≤280 chars.
- No copyrighted material reproduced verbatim.
- Image prompts: no violent, NSFW, or offensive content.
- Include relevant URLs/sources as links.
- Brand voice: professional but engaging.

Return JSON: {{"variants": [{{"platform": "insta|linkedin|twitter", "text": "...", "hashtags": [...], "image_prompt": "..."}}]}}."""


class ContentCreatorAgent(BaseAgent):
    name = "Agent 2: Content Creator"
    description = "Generates platform-specific social media posts with image prompts."
    allowed_tools = ["text_generate", "image_prompt_gen", "optimize_tokens"]

    async def execute(self, input_data: dict) -> dict:
        news_batch_data = input_data.get("news_batch")
        articles = []
        if isinstance(news_batch_data, dict):
            articles = news_batch_data.get("articles", [])
        elif isinstance(news_batch_data, NewsBatch):
            articles = [a.model_dump() for a in news_batch_data.articles]

        session_id = input_data.get("session_id", "default")
        news_ids = [a.get("id", "") for a in articles]

        if self.llm is not None and self.token_manager is not None:
            result = await self.llm_call(
                [{"role": "system", "content": CREATOR_SYSTEM},
                 {"role": "user", "content": f"Create social media content for these articles: {json.dumps(articles[:5], default=str)}"}],
            )
            try:
                data = json.loads(result.text)
            except (json.JSONDecodeError, ValueError):
                data = {"variants": []}
        else:
            data = await self._generate_variants(articles)

        variants: list[PostVariant] = []
        for v in data.get("variants", []):
            platform = self._parse_platform(v.get("platform", "linkedin"))
            text = v.get("text", "")
            hashtags = v.get("hashtags", [])[:5]
            image_prompt = v.get("image_prompt")
            variants.append(
                PostVariant(
                    platform=platform,
                    text=text,
                    hashtags=hashtags,
                    image_prompt=image_prompt,
                    word_count=count_words(text),
                    quality_score=0.0,
                )
            )

        content = SocialContent(
            session_id=session_id,
            news_ids=news_ids,
            variants=variants,
            quality_score=0.0,
        )
        log.info("content_created", variants=len(variants), session=session_id)
        return {"content": content.model_dump()}

    @staticmethod
    def _parse_platform(value: str) -> PlatformType:
        v = value.lower()
        if "insta" in v:
            return PlatformType.INSTAGRAM
        if "linkedin" in v or "linkedin" in v:
            return PlatformType.LINKEDIN
        if "twitter" in v or "tweet" in v or "x" == v:
            return PlatformType.TWITTER
        return PlatformType.LINKEDIN

    async def _generate_variants(self, articles: list[dict]) -> dict:
        """Fallback content generation when no LLM is available."""
        variants = []
        for art in articles[:3]:
            title = art.get("title", "Tech News")
            url = art.get("url", "")
            desc = art.get("description", "")[:200]
            variants.append({
                "platform": "linkedin",
                "text": f"{title}\n\n{desc}\n\nRead more: {url}",
                "hashtags": ["#tech", "#AI", "#news"],
                "image_prompt": f"Professional image about: {title}",
            })
        return {"variants": variants}

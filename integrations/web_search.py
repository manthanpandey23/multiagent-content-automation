"""Web search + RSS / scraping client (DuckDuckGo + BeautifulSoup)."""

from __future__ import annotations
from utils.datetime import utcnow

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from utils.logger import get_logger

log = get_logger("web_search")

try:
    from ddgs import DDGS
    _HAS_DDGS = True
except ImportError:  # pragma: no cover
    try:
        from duckduckgo_search import DDGS  # deprecated alias
        _HAS_DDGS = True
    except ImportError:
        _HAS_DDGS = False


class SearchResult:
    __slots__ = ("title", "href", "body")

    def __init__(self, title: str, href: str, body: str = "") -> None:
        self.title = title
        self.href = href
        self.body = body


class WebSearchClient:
    """Aggregates news via DuckDuckGo search and optional RSS feeds."""

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HermesBot/1.0"

    def __init__(self) -> None:
        self._ddgs: Optional[DDGS] = DDGS() if _HAS_DDGS else None

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        results: list[SearchResult] = []
        if self._ddgs is not None:
            try:
                raw = await asyncio.to_thread(
                    self._ddgs.text, query, max_results=max_results
                )
                for r in raw:
                    results.append(
                        SearchResult(
                            title=r.get("title", ""),
                            href=r.get("href", ""),
                            body=r.get("body", ""),
                        )
                    )
            except Exception as exc:
                log.warning("duckduckgo_search_failed", query=query, error=str(exc))
        if not results:
            results = await self._fallback_search(query, max_results)
        return results

    async def _fallback_search(self, query: str, max_results: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        html_query = query.replace(" ", "+")
        url = f"https://html.duckduckgo.com/html/?q={html_query}"
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": self.USER_AGENT}, timeout=20.0
            ) as client:
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, "html.parser")
                for item in soup.select("a.result__a")[:max_results]:
                    title = item.get_text(strip=True)
                    href = item.get("href", "")
                    results_body = ""
                    next_sib = item.find_next_sibling("div", class_="result__snippet")
                    if next_sib:
                        results_body = next_sib.get_text(strip=True)
                    if href:
                        results.append(SearchResult(title, href, results_body))
        except Exception as exc:
            log.warning("fallback_search_failed", error=str(exc))
        return results

    async def fetch_page(self, url: str, timeout: float = 15.0) -> Optional[str]:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": self.USER_AGENT},
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                if resp.status_code < 400:
                    return resp.text
        except Exception as exc:
            log.warning("fetch_page_failed", url=url, error=str(exc))
        return None

    async def scrape_summary(self, url: str, max_chars: int = 2000) -> str:
        html = await self.fetch_page(url)
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "svg"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:max_chars]

    @staticmethod
    def is_recent(published: Optional[datetime], days: int = 7) -> bool:
        if published is None:
            return True
        return utcnow() - published <= timedelta(days=days)

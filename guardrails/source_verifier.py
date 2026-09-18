"""Source trust scoring and URL verifications guardrail."""

from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from guardrails.base import BaseGuardrail, GuardrailResult, GuardrailSeverity

_TRUSTED_DOMAINS = {
    "techcrunch.com", "arstechnica.com", "theverge.com", "wired.com",
    "zdnet.com", "techradar.com", "engadget.com", "zdnet.com",
    "github.com", "arxiv.org", "medium.com", "dev.to",
}


class SourceVerifierGuardrail(BaseGuardrail):
    """Verifies source URLs resolve and are from trusted domains."""

    name = "source_verifier"
    severity = GuardrailSeverity.CRITICAL

    def __init__(self, trusted: Optional[set[str]] = None, check_url: bool = True) -> None:
        self.trusted = trusted or _TRUSTED_DOMAINS
        self.check_url = check_url

    async def check(self, data: dict, context: Optional[dict] = None) -> GuardrailResult:
        url = data.get("url", "")
        if not url:
            return GuardrailResult(
                name=self.name, passed=False,
                message="No source URL provided",
            )
        domain = self._domain(url)
        score = 1.0 if domain in self.trusted else 0.5
        url_ok = await self._url_reachable(url) if self.check_url else True
        if not url_ok:
            return GuardrailResult(
                name=self.name, passed=False,
                severity=self.severity,
                message=f"URL unreachable: {url}",
                details={"url": url, "trust_score": score},
            )
        return GuardrailResult(
            name=self.name, passed=True,
            message=f"Source '{domain}' trust score {score}",
            details={"url": url, "domain": domain, "trust_score": score},
        )

    @staticmethod
    def _domain(url: str) -> str:
        try:
            from urllib.parse import urlparse

            return urlparse(url).netloc.lower()
        except Exception:
            return ""

    async def _url_reachable(self, url: str, timeout: float = 10.0) -> bool:
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.head(url, headers={"User-Agent": "HermesBot/1.0"})
                return resp.status_code < 400
        except Exception:
            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    resp = await client.get(url, headers={"User-Agent": "HermesBot/1.0"})
                    return resp.status_code < 400
            except Exception:
                return False

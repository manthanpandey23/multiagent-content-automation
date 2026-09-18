"""Word limit enforcement guardrail."""

from __future__ import annotations

from typing import Optional

from config import CONFIG
from utils.text_utils import count_words, truncate_words
from guardrails.base import BaseGuardrail, GuardrailResult, GuardrailSeverity


class WordLimitGuardrail(BaseGuardrail):
    """Enforces title ≤100 words, description ≤300 words (configurable)."""

    name = "word_limit"
    severity = GuardrailSeverity.CRITICAL

    def __init__(self, title_max: int = 100, desc_max: int = 300) -> None:
        self.title_max = CONFIG.title_max_words if title_max == 100 else title_max
        self.desc_max = CONFIG.desc_max_words if desc_max == 300 else desc_max

    async def check(self, data: dict, context: Optional[dict] = None) -> GuardrailResult:
        title = data.get("title", "")
        desc = data.get("description", "")
        title_wc = count_words(title)
        desc_wc = count_words(desc)
        if title_wc > self.title_max or desc_wc > self.desc_max:
            return GuardrailResult(
                name=self.name,
                passed=False,
                severity=self.severity,
                message=f"Word limits exceeded: title={title_wc}/{self.title_max}, desc={desc_wc}/{self.desc_max}",
                details={"title_words": title_wc, "desc_words": desc_wc},
            )
        return GuardrailResult(name=self.name, passed=True, message="Word limits OK")

    async def apply(self, data: dict, context: Optional[dict] = None) -> tuple[dict, GuardrailResult]:
        original = dict(data)
        if count_words(data.get("title", "")) > self.title_max:
            data["title"] = truncate_words(data["title"], self.title_max)
        if count_words(data.get("description", "")) > self.desc_max:
            data["description"] = truncate_words(data["description"], self.desc_max)
        result = await self.check(data, context)
        result.fix_applied = data != original and result.passed
        return data, result

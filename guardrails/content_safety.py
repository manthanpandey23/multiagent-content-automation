"""Content safety guardrail — NSFW / violence / hate-speech filtering."""

from __future__ import annotations

import re
from typing import Optional

from guardrails.base import BaseGuardrail, GuardrailResult, GuardrailSeverity

_BLACKLIST_PATTERNS = [
    r"\bnsfw\b", r"\bviolence\b", r"\bgore\b", r"\bhate\s*speech\b",
    r"\bkill\b", r"\bsexually\b", r"\bpredator\b",
]


class ContentSafetyGuardrail(BaseGuardrail):
    """Blocks content containing harmful/unsafe material."""

    name = "content_safety"
    severity = GuardrailSeverity.CRITICAL

    def __init__(self, patterns: Optional[list[str]] = None) -> None:
        self.patterns = patterns or _BLACKLIST_PATTERNS
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    async def check(self, data: dict, context: Optional[dict] = None) -> GuardrailResult:
        text = " ".join(
            str(v) for v in data.values() if isinstance(v, str)
        )
        matched = [p.pattern for p in self._compiled if p.search(text)]
        if matched:
            return GuardrailResult(
                name=self.name,
                passed=False,
                severity=self.severity,
                message=f"Unsafe content detected: {matched}",
                details={"matches": matched},
            )
        return GuardrailResult(name=self.name, passed=True, message="Content safe")

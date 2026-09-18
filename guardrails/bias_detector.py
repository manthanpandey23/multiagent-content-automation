"""Bias detection and tone/factuality analysis guardrail."""

from __future__ import annotations

import re
from typing import Optional

from guardrails.base import BaseGuardrail, GuardrailResult, GuardrailSeverity

_BIAS_MARKERS = [
    r"\b(shocking|unbelievable|you won't believe)\b",
    r"\bbest.*ever\b",
    r"\bguarantee(d)?\b",
    r"\b(revolutionary|game-changing)\s*without\b",
    r"\b(he said|she said)\s*:\s*",
]


class BiasDetectorGuardrail(BaseGuardrail):
    """Detects sensationalism, bias, and verifies factual tone."""

    name = "bias_detector"
    severity = GuardrailSeverity.WARN

    def __init__(self, patterns: Optional[list[str]] = None) -> None:
        self.patterns = patterns or _BIAS_MARKERS
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    async def check(self, data: dict, context: Optional[dict] = None) -> GuardrailResult:
        text = data.get("text", "") or " ".join(
            str(v) for v in data.values() if isinstance(v, str)
        )
        matched = [p.pattern for p in self._compiled if p.search(text)]
        if matched:
            return GuardrailResult(
                name=self.name,
                passed=False,
                severity=GuardrailSeverity.WARN,
                message=f"Potential bias/sensationalism detected: {matched}",
                details={"matches": matched},
            )
        return GuardrailResult(name=self.name, passed=True, message="No bias markers detected")

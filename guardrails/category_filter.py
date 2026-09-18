"""Category scope enforcement guardrail."""

from __future__ import annotations

from typing import Optional

from config import CONFIG
from guardrails.base import BaseGuardrail, GuardrailResult, GuardrailSeverity


_ALLOWED_CATEGORIES = {
    "AI", "Generative AI", "Machine Learning", "LLM", "AI Agents",
    "Automation", "Cloud Computing", "Cybersecurity",
    "Software Engineering", "Developer Tools", "IT Sector",
}


class CategoryFilterGuardrail(BaseGuardrail):
    """Only allows news from the configured allowed-category list."""

    name = "category_filter"
    severity = GuardrailSeverity.CRITICAL

    def __init__(self, allowed: Optional[list[str]] = None) -> None:
        self.allowed = set(allowed) if allowed else set(_ALLOWED_CATEGORIES)

    async def check(self, data: dict, context: Optional[dict] = None) -> GuardrailResult:
        category = data.get("category", "")
        if not category or category not in self.allowed:
            return GuardrailResult(
                name=self.name,
                passed=False,
                severity=self.severity,
                message=f"Category '{category}' not in allowed list",
                details={"category": category, "allowed": sorted(self.allowed)},
            )
        return GuardrailResult(name=self.name, passed=True, message=f"Category '{category}' OK")

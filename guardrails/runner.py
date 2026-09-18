"""Guardrail runner that executes all guardrails against agent output."""

from __future__ import annotations

from typing import Optional

from guardrails.base import BaseGuardrail, GuardrailResult, GuardrailSeverity
from guardrails.word_limit import WordLimitGuardrail
from guardrails.category_filter import CategoryFilterGuardrail
from guardrails.content_safety import ContentSafetyGuardrail
from guardrails.source_verifier import SourceVerifierGuardrail
from guardrails.bias_detector import BiasDetectorGuardrail


class GuardrailRunner:
    """Runs a configured set of guardrails against data."""

    def __init__(self, guardrails: Optional[list[BaseGuardrail]] = None) -> None:
        self.guardrails: list[BaseGuardrail] = guardrails or self._default_guardrails()

    @staticmethod
    def _default_guardrails() -> list[BaseGuardrail]:
        return [
            WordLimitGuardrail(),
            CategoryFilterGuardrail(),
            ContentSafetyGuardrail(),
            SourceVerifierGuardrail(),
            BiasDetectorGuardrail(),
        ]

    async def run_all(self, data: dict, context: Optional[dict] = None) -> list[GuardrailResult]:
        results: list[GuardrailResult] = []
        for guardrail in self.guardrails:
            try:
                _, result = await guardrail.apply(data, context)
                results.append(result)
            except Exception as exc:
                results.append(
                    GuardrailResult(
                        name=guardrail.name,
                        passed=False,
                        severity=GuardrailSeverity.WARN,
                        message=f"Guardrail error: {exc}",
                    )
                )
        return results

    @staticmethod
    def has_critical_failure(results: list[GuardrailResult]) -> bool:
        return any(
            not r.passed and r.severity == GuardrailSeverity.CRITICAL for r in results
        )

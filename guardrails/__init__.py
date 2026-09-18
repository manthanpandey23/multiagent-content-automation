"""Guardrail system — bounded validation checks for agent outputs.

Every guardrail implements :class:`BaseGuardrail` and returns a
:class:`GuardrailResult` indicating pass/fail with an optional auto-fix.
"""

from guardrails.base import BaseGuardrail, GuardrailResult, GuardrailSeverity
from guardrails.word_limit import WordLimitGuardrail
from guardrails.category_filter import CategoryFilterGuardrail
from guardrails.content_safety import ContentSafetyGuardrail
from guardrails.source_verifier import SourceVerifierGuardrail
from guardrails.bias_detector import BiasDetectorGuardrail
from guardrails.runner import GuardrailRunner

__all__ = [
    "BaseGuardrail",
    "GuardrailResult",
    "GuardrailSeverity",
    "WordLimitGuardrail",
    "CategoryFilterGuardrail",
    "ContentSafetyGuardrail",
    "SourceVerifierGuardrail",
    "BiasDetectorGuardrail",
    "GuardrailRunner",
]

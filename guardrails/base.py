"""Base guardrail class and result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class GuardrailSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


@dataclass
class GuardrailResult:
    name: str
    passed: bool
    severity: GuardrailSeverity = GuardrailSeverity.INFO
    message: str = ""
    fix_applied: bool = False
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "fix_applied": self.fix_applied,
            "details": self.details,
        }


class BaseGuardrail(ABC):
    """All guardrails implement this interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def severity(self) -> GuardrailSeverity:
        ...

    @abstractmethod
    async def check(self, data: dict, context: Optional[dict] = None) -> GuardrailResult:
        ...

    async def apply(self, data: dict, context: Optional[dict] = None) -> tuple[dict, GuardrailResult]:
        """Check and optionally auto-fix. Returns (possibly_modified_data, result)."""
        result = await self.check(data, context)
        return data, result

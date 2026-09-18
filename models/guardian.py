"""Guardian (safeguard agent) data models."""

from __future__ import annotations
from utils.datetime import utcnow

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GuardianSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class GuardianChecklist(BaseModel):
    allowed_tools_only: bool = True
    within_scope: bool = True
    token_budget_ok: bool = True
    no_loop_detected: bool = True
    data_access_right: bool = True
    no_self_modify: bool = True
    no_permission_escalation: bool = True
    output_matches_input: bool = True


class GuardianAlert(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    session_id: str
    agent_name: str
    execution_id: str
    severity: GuardianSeverity = GuardianSeverity.WARN
    violation: str
    attempted_tool: Optional[str] = None
    allowed_tools: list[str] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    checklist: GuardianChecklist = Field(default_factory=GuardianChecklist)
    recommended_action: str = "ALLOW"
    created_at: datetime = Field(default_factory=utcnow)


class GuardianReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    period_start: datetime
    period_end: datetime
    total_checks: int = 0
    violations: int = 0
    critical_count: int = 0
    warn_count: int = 0
    info_count: int = 0
    compliance_score: float = 100.0
    per_agent_summary: dict = Field(default_factory=dict)
    alerts: list[GuardianAlert] = Field(default_factory=list)

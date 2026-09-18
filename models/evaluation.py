"""Evaluation data models."""

from __future__ import annotations
from utils.datetime import utcnow

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReportPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    RUN = "run"


class RubricScore(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rubric_name: str
    metric_name: str
    score: float
    weight: float
    weighted_score: float
    passed: bool
    evidence: Optional[str] = None


class EvalResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    session_id: str
    eval_type: ReportPeriod = ReportPeriod.RUN
    period_start: datetime
    period_end: datetime
    overall_score: float = 0.0
    category_scores: dict = Field(default_factory=dict)
    agent_scores: dict = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    trend_vs_previous: dict = Field(default_factory=dict)
    report_data: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)

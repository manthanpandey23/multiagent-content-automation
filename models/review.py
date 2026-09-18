"""Review data models."""

from __future__ import annotations
from utils.datetime import utcnow

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewerType(str, Enum):
    AUTO = "auto"
    HUMAN = "human"


class ReviewStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    session_id: str
    agent_name: str
    reviewer_type: ReviewerType = ReviewerType.AUTO
    score: float = 0.0
    status: ReviewStatus = ReviewStatus.WARN
    feedback: str = ""
    flags: list[str] = Field(default_factory=list)
    dimensions: dict[str, float] = Field(default_factory=dict)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    action_taken: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

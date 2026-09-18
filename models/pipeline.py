"""Pipeline state data models."""

from __future__ import annotations
from utils.datetime import utcnow

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PipelineStage(str, Enum):
    IDLE = "idle"
    RESEARCHING = "researching"
    RESEARCH_REVIEW = "research_review"
    HUMAN_REVIEW_RESEARCH = "human_research"
    CREATING = "creating"
    CREATING_REVIEW = "creating_review"
    HUMAN_REVIEW_CREATING = "human_creating"
    VALIDATING = "validating"
    VALIDATING_REVIEW = "validating_review"
    HUMAN_REVIEW_VALIDATING = "human_validating"
    PUBLISHING = "publishing"
    GUARDIAN_CHECK = "guardian_check"
    COMPLETE = "complete"
    FAILED = "failed"


class PipelineStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineState(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    chat_id: Optional[int] = None
    current_stage: PipelineStage = PipelineStage.IDLE
    status: PipelineStatus = PipelineStatus.RUNNING
    news_category: Optional[str] = None
    published_platforms: list[str] = Field(default_factory=list)
    publish_results: dict = Field(default_factory=dict)
    review_decisions: list[dict] = Field(default_factory=list)
    approvals: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

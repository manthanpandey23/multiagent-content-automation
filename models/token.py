"""Token management data models."""

from __future__ import annotations
from utils.datetime import utcnow

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProviderName(str, Enum):
    NVIDIA = "nvidia"
    OPENROUTER = "openrouter"


class BudgetStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class TokenUsage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    agent_name: str
    provider: ProviderName
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached: bool = False
    response_time_ms: int = 0
    estimated_cost: float = 0.0
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class TokenBudget(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    agent_name: str
    provider: ProviderName = ProviderName.NVIDIA
    model: str
    daily_limit: int = 500000
    spent_today: int = 0
    remaining_today: int = 500000
    last_reset: datetime = Field(default_factory=utcnow)
    status: BudgetStatus = BudgetStatus.HEALTHY
    updated_at: datetime = Field(default_factory=utcnow)


class ProviderCapacity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    provider: ProviderName
    model: str
    tokens_per_minute: int
    requests_per_day: int
    currently_available: bool = True
    health_status: str = "healthy"
    last_checked: datetime = Field(default_factory=utcnow)


class RouteDecision(BaseModel):
    provider: ProviderName
    model: str
    reason: str = ""
    switched: bool = False

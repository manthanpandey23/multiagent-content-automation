"""SQLAlchemy ORM models for all pipeline entities.

These are the persistent database tables.  The Pydantic schemas in
``models/`` are the data-transfer contracts; repositories convert between
the two layers.
"""

from __future__ import annotations
from utils.datetime import utcnow

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    JSON,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base

from models.token import ProviderName, BudgetStatus

Base = declarative_base()


def _uuid() -> str:
    return uuid.uuid4().hex


class NewsArticleOrm(Base):
    __tablename__ = "news_articles"

    id = Column(String(36), primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String(200), nullable=False)
    url = Column(String(2000), nullable=False, unique=True)
    published_time = Column(DateTime, nullable=False)
    category = Column(String(100), nullable=False)
    fetched_at = Column(DateTime, default=utcnow)
    session_id = Column(String(36), index=True)

    __table_args__ = (Index("ix_news_url", "url"),)


class PostVariantOrm(Base):
    __tablename__ = "post_variants"

    id = Column(String(36), primary_key=True, default=_uuid)
    content_id = Column(String(36), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    hashtags = Column(ARRAY(String(50)), default=[])
    image_prompt = Column(Text)
    word_count = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)


class SocialContentOrm(Base):
    __tablename__ = "social_content"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), nullable=False, index=True)
    news_ids = Column(ARRAY(String(36)), default=[])
    quality_score = Column(Float, default=0.0)
    validation_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=utcnow)


class ReviewRecordOrm(Base):
    __tablename__ = "review_records"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    reviewer_type = Column(String(20), default="auto")
    score = Column(Float, default=0.0)
    status = Column(String(20), default="warn")
    feedback = Column(Text, default="")
    flags = Column(ARRAY(String(200)), default=[])
    dimensions = Column(JSON, default={})
    approved_by = Column(String(200))
    approved_at = Column(DateTime)
    action_taken = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_review_session", "session_id"),)


class PipelineStateOrm(Base):
    __tablename__ = "pipeline_state"

    session_id = Column(String(36), primary_key=True, default=_uuid)
    chat_id = Column(Integer)
    current_stage = Column(String(100), default="idle")
    status = Column(String(50), default="running")
    news_category = Column(String(500))
    published_platforms = Column(ARRAY(String(50)), default=[])
    publish_results = Column(JSON, default={})
    review_decisions = Column(JSON, default=[])
    approvals = Column(JSON, default={})
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow)


class GuardianAlertOrm(Base):
    __tablename__ = "guardian_alerts"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    execution_id = Column(String(36), nullable=False)
    severity = Column(String(20), default="warn")
    violation = Column(Text, nullable=False)
    attempted_tool = Column(String(200))
    allowed_tools = Column(ARRAY(String(200)), default=[])
    context = Column(JSON, default={})
    checklist = Column(JSON, default={})
    recommended_action = Column(String(50), default="ALLOW")
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_guardian_session", "session_id"),)


class EvalResultOrm(Base):
    __tablename__ = "eval_results"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), nullable=False, index=True)
    eval_type = Column(String(20), default="run")
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    overall_score = Column(Float, default=0.0)
    category_scores = Column(JSON, default={})
    agent_scores = Column(JSON, default={})
    recommendations = Column(ARRAY(String(1000)), default=[])
    trend_vs_previous = Column(JSON, default={})
    report_data = Column(JSON, default={})
    created_at = Column(DateTime, default=utcnow)


class RubricCheckpointOrm(Base):
    __tablename__ = "rubric_checkpoints"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(100))
    metric_name = Column(String(200), nullable=False)
    score = Column(Float)
    weight = Column(Float)
    weighted_score = Column(Float)
    passed = Column(Boolean, default=False)
    evidence = Column(Text)
    created_at = Column(DateTime, default=utcnow)


class TokenUsageOrm(Base):
    __tablename__ = "token_usage"

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_name = Column(String(100), nullable=False)
    provider = Column(SAEnum(ProviderName), default=ProviderName.NVIDIA)
    model = Column(String(200))
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    cached = Column(Boolean, default=False)
    response_time_ms = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    session_id = Column(String(36), index=True)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_token_usage_session", "session_id"),)


class TokenBudgetOrm(Base):
    __tablename__ = "token_budgets"

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_name = Column(String(100), unique=True, nullable=False)
    provider = Column(SAEnum(ProviderName), default=ProviderName.NVIDIA)
    model = Column(String(200))
    daily_limit = Column(Integer, default=500000)
    spent_today = Column(Integer, default=0)
    remaining_today = Column(Integer, default=500000)
    last_reset = Column(DateTime, default=utcnow)
    status = Column(SAEnum(BudgetStatus), default=BudgetStatus.HEALTHY)
    updated_at = Column(DateTime, default=utcnow)


class ProviderCapacityOrm(Base):
    __tablename__ = "provider_capacities"

    id = Column(String(36), primary_key=True, default=_uuid)
    provider = Column(SAEnum(ProviderName), default=ProviderName.NVIDIA)
    model = Column(String(200), nullable=False)
    tokens_per_minute = Column(Integer)
    requests_per_day = Column(Integer)
    currently_available = Column(Boolean, default=True)
    health_status = Column(String(30), default="healthy")
    last_checked = Column(DateTime, default=utcnow)

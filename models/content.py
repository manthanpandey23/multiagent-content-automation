"""Social content data models."""

from __future__ import annotations
from utils.datetime import utcnow

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PlatformType(str, Enum):
    INSTAGRAM = "insta"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"


class PostVariant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    platform: PlatformType
    text: str
    hashtags: list[str] = Field(default_factory=list)
    image_prompt: Optional[str] = None
    word_count: int = 0
    quality_score: float = 0.0


class SocialContent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    session_id: str
    news_ids: list[str] = Field(default_factory=list)
    variants: list[PostVariant] = Field(default_factory=list)
    quality_score: float = 0.0
    validation_status: str = "pending"
    created_at: datetime = Field(default_factory=utcnow)


class PublishResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    session_id: str
    platform: PlatformType
    success: bool
    post_url: Optional[str] = None
    post_id: Optional[str] = None
    error: Optional[str] = None
    published_at: datetime = Field(default_factory=utcnow)

"""News data models."""

from __future__ import annotations
from utils.datetime import utcnow

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NewsCategory(str, Enum):
    AI = "AI"
    GENERATIVE_AI = "Generative AI"
    MACHINE_LEARNING = "Machine Learning"
    LLM = "LLM"
    AI_AGENTS = "AI Agents"
    AUTOMATION = "Automation"
    CLOUD = "Cloud Computing"
    CYBERSECURITY = "Cybersecurity"
    SOFTWARE_ENGINEERING = "Software Engineering"
    DEVELOPER_TOOLS = "Developer Tools"
    IT_SECTOR = "IT Sector"


class NewsArticle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    title: str
    description: str
    source: str
    url: str
    published_time: datetime
    category: str
    fetched_at: datetime = Field(default_factory=utcnow)
    session_id: Optional[str] = None


class NewsBatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    articles: list[NewsArticle]
    category: Optional[str] = None

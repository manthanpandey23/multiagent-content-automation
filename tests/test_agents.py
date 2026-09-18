"""Tests for agents using offline fallback logic."""

import asyncio

import pytest

from agents.creator import ContentCreatorAgent
from agents.validator import ContentValidatorAgent
from agents.reviewer import AgentReviewer
from models.content import SocialContent, PostVariant, PlatformType


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_creator_generates_variants():
    creator = ContentCreatorAgent()
    sample = {
        "articles": [
            {
                "id": "1",
                "title": "AI breakthrough",
                "description": "New model demonstrates advanced reasoning capabilities.",
                "source": "techcrunch.com",
                "url": "https://techcrunch.com/ai",
                "category": "AI",
            }
        ]
    }
    result = _run(creator.execute({"news_batch": sample, "session_id": "test"}))
    content = result["content"]
    assert "variants" in content
    assert len(content["variants"]) >= 1
    variant = content["variants"][0]
    assert "platform" in variant
    assert len(variant["text"]) > 0


def test_validator_fixes_format():
    validator = ContentValidatorAgent()
    long_text = "word " * 300  # 300 words, exceeds twitter limit
    content = SocialContent(
        session_id="test",
        news_ids=["1"],
        variants=[
            PostVariant(platform=PlatformType.TWITTER, text=long_text, hashtags=["#a"]),
            PostVariant(platform=PlatformType.LINKEDIN, text="Short post.", hashtags=["#b"]),
        ],
        quality_score=50.0,
        validation_status="pending",
    )
    result = _run(validator.execute({"content": content.model_dump(), "session_id": "test"}))
    assert "validation_report" in result
    assert result["validation_report"]["score"] >= 0


def test_reviewer_heuristic_without_llm():
    reviewer = AgentReviewer()
    result = _run(reviewer.execute({
        "agent_name": "TestAgent",
        "output_data": {"text": "valid content"},
        "session_id": "test",
    }))
    assert "score" in result
    assert "status" in result
    assert "passed" in result

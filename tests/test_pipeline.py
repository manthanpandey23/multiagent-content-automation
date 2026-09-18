"""Tests for the pipeline orchestrator (state machine & routing)."""

import asyncio
import json
from datetime import datetime

import pytest

from pipeline import PipelineOrchestrator, _json_safe
from models.pipeline import PipelineState, PipelineStage


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_json_safe_converts_datetime():
    data = {"created_at": datetime(2025, 1, 1, 12, 0, 0), "name": "test"}
    safe = _json_safe(data)
    encoded = json.dumps(safe)
    assert "test" in encoded
    assert "2025" in encoded


def test_json_safe_handles_nested():
    data = {"items": [{"time": datetime(2025, 1, 1)}], "count": 3}
    safe = _json_safe(data)
    json.dumps(safe)


def test_create_session():
    orch = PipelineOrchestrator()
    sid = orch.create_session()
    assert sid
    state = orch.get_session(sid)
    assert state is not None
    assert state.current_stage == PipelineStage.IDLE


def test_run_stage_unknown_raises():
    orch = PipelineOrchestrator()
    with pytest.raises(ValueError, match="Unknown stage"):
        _run(orch.run_stage("nonexistent_stage", None, {}))


@pytest.mark.asyncio
async def test_human_review_auto_approve_dry_run(monkeypatch):
    from config import CONFIG

    monkeypatch.setattr(CONFIG, "dry_run", True)
    orch = PipelineOrchestrator()
    state = PipelineState(session_id="test-session")
    orch._sessions["test-session"] = state
    approved = await orch._human_review(state, "Test Stage", {"content": "test"})
    assert approved is True
    assert "Test Stage" in state.approvals


@pytest.mark.asyncio
async def test_stage_routing_research(monkeypatch):
    from config import CONFIG

    monkeypatch.setattr(CONFIG, "dry_run", True)
    orch = PipelineOrchestrator()

    class _FakeSearch:
        async def search(self, query, max_results=10):
            return []
        async def scrape_summary(self, url, max_chars=2000):
            return "fake summary"
    orch.researcher.search = _FakeSearch()
    result = await asyncio.wait_for(orch.run_stage("research", None, {}), timeout=30)
    assert "news_batch" in result
    assert result["approved"] is True


@pytest.mark.asyncio
async def test_guardian_interception_detects_violation():
    orch = PipelineOrchestrator()
    report = await orch.guardian.post_execution_hook(
        "TestAgent", "exec1", {"input": "x"}, {"output": "y"},
        tools_called=["file_write", "web_search"],
        allowed_tools=["web_search"],
        token_usage=1000,
        session_id="test",
    )
    assert report.violations == 1
    assert report.critical_count == 1


@pytest.mark.asyncio
async def test_guardian_interception_clean_run():
    orch = PipelineOrchestrator()
    report = await orch.guardian.post_execution_hook(
        "TestAgent", "exec2", {"input": "x"}, {"output": "y"},
        tools_called=["web_search"],
        allowed_tools=["web_search"],
        token_usage=1000,
        session_id="test",
    )
    assert report.violations == 0
    assert report.compliance_score == 100.0

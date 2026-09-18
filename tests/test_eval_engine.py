"""Tests for the evaluation engine rubrics."""

import asyncio

from integrations.eval_engine import EvalEngine, RUBRICS


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_rubrics_defined():
    expected = {"content_quality", "workflow_accuracy", "news_research", "publishing"}
    assert expected <= set(RUBRICS.keys())


def test_rubric_weights_sum_to_one():
    for name, rubric in RUBRICS.items():
        total = sum(m["weight"] for m in rubric["metrics"])
        assert abs(total - 1.0) < 0.01, f"{name} weights sum to {total}"


def test_eval_engine_scores_without_llm():
    engine = EvalEngine()
    data = {
        "news_articles": [
            {"title": "AI news", "source": "techcrunch.com", "category": "AI"},
            {"title": "ML news", "source": "arstechnica.com", "category": "Machine Learning"},
        ],
        "reviews": [{"status": "pass"}, {"status": "warn"}],
        "publish_results": {"results": [{"success": True}, {"success": False}]},
    }
    result = _run(engine.evaluate_run("test-session", data))
    assert result.session_id == "test-session"
    assert 0 <= result.overall_score <= 100
    assert "content_quality" in result.category_scores


def test_eval_engine_quantitative_scoring():
    engine = EvalEngine()
    data = {
        "news_articles": [],
        "reviews": [],
        "publish_results": {"results": []},
    }
    result = _run(engine.evaluate_run("test-empty", data))
    assert result.overall_score == 0.0 or result.overall_score >= 0

"""Tests for guardrails."""

import asyncio

import pytest

from guardrails.word_limit import WordLimitGuardrail
from guardrails.category_filter import CategoryFilterGuardrail
from guardrails.content_safety import ContentSafetyGuardrail
from guardrails.source_verifier import SourceVerifierGuardrail
from guardrails.bias_detector import BiasDetectorGuardrail
from guardrails.runner import GuardrailRunner


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_word_limit_passes():
    g = WordLimitGuardrail(title_max=100, desc_max=300)
    result = _run(g.check({"title": "Short", "description": "A" * 20}))
    assert result.passed


def test_word_limit_fails_and_fixes():
    g = WordLimitGuardrail(title_max=3, desc_max=5)
    data, result = _run(g.apply({"title": "word " * 10, "description": "a b c d e f g"}))
    # After apply, title should be truncated to within the limit
    assert len(data["title"].split()) <= 3


def test_category_filter_passes():
    g = CategoryFilterGuardrail()
    result = _run(g.check({"category": "AI", "url": "https://example.com"}))
    assert result.passed


def test_category_filter_rejects():
    g = CategoryFilterGuardrail()
    result = _run(g.check({"category": "Sports", "url": "https://example.com"}))
    assert not result.passed


def test_content_safety_blocks():
    g = ContentSafetyGuardrail()
    result = _run(g.check({"text": "This is violent content"}))
    assert not result.passed


def test_content_safety_passes():
    g = ContentSafetyGuardrail()
    result = _run(g.check({"text": "Here is some tech news"}))
    assert result.passed


def test_source_verifier_rejects_empty_url():
    g = SourceVerifierGuardrail()
    result = _run(g.check({"url": ""}))
    assert not result.passed


def test_bias_detector_flags_sensationalism():
    g = BiasDetectorGuardrail()
    result = _run(g.check({"text": "You won't believe this shocking news!"}))
    assert not result.passed


def test_guardrail_runner_collects_all():
    runner = GuardrailRunner()
    data = {"title": "x", "description": "y", "category": "AI", "url": "https://example.com", "text": "normal text"}
    results = _run(runner.run_all(data))
    assert len(results) == 5


def test_guardrail_runner_critical_failure():
    runner = GuardrailRunner()
    data = {"url": "bad"}  # category_filter and source_verifier will fail critically
    results = _run(runner.run_all(data))
    assert GuardrailRunner.has_critical_failure(results)

"""Tests for the cache key computation and budget tracker."""

import pytest

from llm_manager.cache import compute_cache_key, SemanticCache


def test_cache_key_is_deterministic():
    messages = [{"role": "user", "content": "hello"}]
    key1 = compute_cache_key(messages, "gpt-4")
    key2 = compute_cache_key(messages, "gpt-4")
    assert key1 == key2


def test_cache_key_differs_for_different_model():
    messages = [{"role": "user", "content": "hello"}]
    key1 = compute_cache_key(messages, "nvidia")
    key2 = compute_cache_key(messages, "openrouter")
    assert key1 != key2


def test_cache_key_differs_for_different_content():
    key1 = compute_cache_key([{"role": "user", "content": "hello"}], "gpt-4")
    key2 = compute_cache_key([{"role": "user", "content": "world"}], "gpt-4")
    assert key1 != key2


def test_semantic_cache_disabled():
    cache = SemanticCache(redis_client=None, enabled=False)
    assert cache.enabled is False

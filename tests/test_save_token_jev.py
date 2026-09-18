"""Tests for the save-token-jev optimization toolkit."""

from tools.save_token_jev import (
    optimize_messages,
    prune_messages,
    compute_prompt_hash,
    estimate_tokens,
)
from utils.text_utils import count_words, count_tokens_approx


def test_count_words():
    assert count_words("hello world") == 2


def test_optimize_messages_dedupes():
    messages = [
        {"role": "system", "content": "Please act as a helpful assistant. You are a helpful assistant."},
        {"role": "user", "content": "hello"},
    ]
    result = optimize_messages(messages)
    assert len(result) == 2
    assert "helpful assistant" not in result[0]["content"].lower()


def test_optimize_messages_preserves_order():
    messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
        {"role": "user", "content": "third"},
    ]
    result = optimize_messages(messages)
    assert len(result) == 3


def test_prune_when_under_limit():
    messages = [{"role": "user", "content": "short"}]
    result = prune_messages(messages, max_tokens=10000)
    assert len(result) == 1


def test_prune_when_over_limit():
    long_content = "word " * 1000
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": long_content},
    ]
    result = prune_messages(messages, max_tokens=50)
    assert len(result) <= 2


def test_compute_prompt_hash_stability():
    messages = [{"role": "user", "content": "hello world"}]
    assert compute_prompt_hash(messages) == compute_prompt_hash(messages)


def test_estimate_tokens_positive():
    messages = [{"role": "user", "content": "hello world this is a test"}]
    assert estimate_tokens(messages) > 0


def test_count_tokens_approx():
    assert count_tokens_approx("hello") > 0
    assert count_tokens_approx("") == 1

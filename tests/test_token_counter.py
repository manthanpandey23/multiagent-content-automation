"""Tests for the token counter."""

from llm_manager.counter import TokenCounter


def test_count_basic():
    counter = TokenCounter()
    tokens = counter.count("hello world, this is a test")
    assert tokens > 0


def test_count_empty():
    counter = TokenCounter()
    assert counter.count("") == 0


def test_count_messages():
    counter = TokenCounter()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello there"},
    ]
    total = counter.count_messages(messages)
    assert total > 10


def test_estimate_response():
    counter = TokenCounter()
    assert counter.estimate_response(1000, "meta/llama-3.1-8b-instruct") > 0


def test_count_approx():
    from utils.text_utils import count_tokens_approx

    assert count_tokens_approx("hello world") > 0

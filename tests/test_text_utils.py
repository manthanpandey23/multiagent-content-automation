"""Tests for text utilities."""

from utils.text_utils import count_words, truncate_words, enforce_word_limit, compute_similarity


def test_count_words():
    assert count_words("") == 0
    assert count_words("hello world") == 2
    assert count_words("one two three four five") == 5


def test_truncate_words():
    text = "one two three four five"
    assert truncate_words(text, 3) == "one two three"
    assert truncate_words(text, 10) == text


def test_enforce_word_limit_truncates():
    long = "word " * 50  # 50 words
    result = enforce_word_limit(long, 10, "title")
    assert count_words(result) == 10


def test_enforce_word_limit_passthrough():
    short = "hello world"
    assert enforce_word_limit(short, 100) == short


def test_compute_similarity():
    assert compute_similarity("hello world", "hello world") == 1.0
    assert compute_similarity("hello world", "goodbye world") == 1 / 3
    assert compute_similarity("", "") == 0.0

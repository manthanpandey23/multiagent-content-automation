"""Text utilities: word counting, truncation, and limit enforcement."""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\S+")


def count_words(text: str) -> int:
    if not text:
        return 0
    return len(_TOKEN_RE.findall(text))


def count_tokens_approx(text: str) -> int:
    """Rough approximation: ~4 chars per token."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def enforce_word_limit(text: str, max_words: int, field_name: str = "text") -> str:
    """Hard-enforce a word limit, truncating if necessary."""
    if count_words(text) > max_words:
        return truncate_words(text, max_words)
    return text


def compute_similarity(a: str, b: str) -> float:
    """Jaccard similarity of word sets, 0.0–1.0."""
    if not a or not b:
        return 0.0
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)

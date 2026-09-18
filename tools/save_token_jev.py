"""save-token-jev — token optimization toolkit shared by all agents.

Provides helper functions to reduce token waste before LLM calls:
pruning, summarization, deduplication, and prompt hashing for the
semantic cache.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:  # pragma: no cover
    _HAS_TIKTOKEN = False

from utils.logger import get_logger

log = get_logger("save_token_jev")

_ROLE_ORDER = {"system": 0, "user": 1, "assistant": 2, "function": 3, "tool": 4}

_REDUNDANT_INSTRUCTION_RE = re.compile(
    r"\b(you are a helpful assistant|as an ai|please act as|follow the instructions below)\b",
    re.IGNORECASE,
)


def _count_with_tiktoken(text: str, model: str = "gpt-4") -> int:
    if not _HAS_TIKTOKEN:
        return len(text) // 4
    try:
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))


def estimate_tokens(messages: list[dict], model: str = "gpt-4") -> int:
    """Estimate total tokens for a message list (rough chat-aware heuristic)."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += _count_with_tiktoken(content, model)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    total += _count_with_tiktoken(part["text"], model)
        total += 4
    return total


def compute_prompt_hash(messages: list[dict], model: str = "gpt-4") -> str:
    """SHA-256 hash of the canonical message text for semantic cache keys."""
    payload = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def prune_messages(
    messages: list[dict], max_tokens: int, model: str = "gpt-4"
) -> list[dict]:
    """Prune older non-system messages when approaching a token ceiling.

    Always preserves the system prompt plus the most recent messages.
    """
    if not messages:
        return messages
    system_index = next(
        (i for i, m in enumerate(messages) if m.get("role") == "system"), None
    )
    ordered = sorted(
        enumerate(messages),
        key=lambda pair: (_ROLE_ORDER.get(pair[1].get("role", ""), 9), -pair[0]),
    )
    kept: list[dict] = []
    total = 0
    for idx, msg in ordered:
        cost = _count_with_tiktoken(msg.get("content", ""), model) if msg.get("content") else 4
        if total + cost > max_tokens and len(kept) >= 2:
            break
        kept.append(msg)
        total += cost
    if system_index is not None and messages[system_index] not in kept:
        kept.insert(0, messages[system_index])
    kept.sort(key=lambda m: messages.index(m) if m in messages else 0)
    return kept


def summarize_context(messages: list[dict], max_sentences: int = 5) -> str:
    """Produce a short bullet-point summary of a message list."""
    full = " ".join(
        m.get("content", "") for m in messages if m.get("content")
    )
    sentences = re.split(r"(?<=[.!?])\s+", full)[:max_sentences]
    bullets = [f"- {s.strip()}" for s in sentences if s.strip()]
    return "\n".join(bullets) if bullets else "Summary unavailable."


def dedupe_instructions(system_prompt: str) -> str:
    """Remove redundant instruction phrases from a system prompt."""
    result = system_prompt
    for marker in ("You are", "You should", "Please act as"):
        if result.count(marker) > 1:
            parts = result.split(marker)
            result = marker + "".join(parts[2:])
    return result.strip()


def optimize_messages(
    messages: list[dict],
    max_tokens: Optional[int] = None,
    model: str = "gpt-4",
) -> list[dict]:
    """End-to-end message optimization: dedupe, prune, summarize.

    Called by ``BaseAgent.optimize_tokens`` before every LLM invocation.
    """
    if not messages:
        return messages
    optimized = []
    for msg in messages:
        new_msg = dict(msg)
        content = new_msg.get("content")
        if isinstance(content, str):
            new_msg["content"] = _REDUNDANT_INSTRUCTION_RE.sub("", content).strip()
            if new_msg.get("role") == "system":
                new_msg["content"] = dedupe_instructions(new_msg["content"])
        optimized.append(new_msg)
    if max_tokens is not None:
        current = estimate_tokens(optimized, model)
        if current > max_tokens:
            log.info(
                "context_pruned",
                before=current,
                after=max_tokens,
                model=model,
            )
            optimized = prune_messages(optimized, max_tokens, model)
    return optimized


def is_redundant_query(prompt_hash: str, recent_hashes: list[str]) -> bool:
    """Return True if a prompt matches a previously-seen prompt (cache hit)."""
    return prompt_hash in recent_hashes

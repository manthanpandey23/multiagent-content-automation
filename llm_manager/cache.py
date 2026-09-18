"""Semantic caching layer for LLM responses.

Cache key = SHA-256 of the tiktoken-encoded prompt, enabling reuse of
responses for similar queries across agents.
"""

from __future__ import annotations

import time
from typing import Optional

import xxhash

from config import CONFIG
from utils.logger import get_logger

log = get_logger("semantic_cache")


def compute_cache_key(messages: list[dict], model: str = "gpt-4") -> str:
    payload = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
    )
    return f"{xxhash.xxh3_64(payload.encode('utf-8'), seed=0).hexdigest()}:{model}"


class SemanticCache:
    def __init__(self, redis_client, enabled: Optional[bool] = None) -> None:
        self.redis = redis_client
        self.enabled = CONFIG.token_cache_enabled if enabled is None else enabled
        self.ttl_hours = CONFIG.token_cache_ttl_hours
        self.ttl_long = CONFIG.token_cache_ttl_long

    def _prefix(self, model: str, long_ttl: bool = False) -> str:
        ttl_tag = "long" if long_ttl else "short"
        return f"cache:llm:{model}:{ttl_tag}"

    async def get(self, cache_key: str, model: str = "gpt-4") -> Optional[str]:
        if not self.enabled or self.redis is None:
            return None
        try:
            val = self.redis.get(f"{self._prefix(model)}:{cache_key}")
            if val is None:
                return None
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            return val
        except Exception as exc:
            log.warning("cache_get_failed", error=str(exc))
            return None

    async def set(self, cache_key: str, response: str, model: str = "gpt-4", long_ttl: bool = False) -> None:
        if not self.enabled or self.redis is None:
            return
        try:
            ttl = long_ttl and self.ttl_long * 3600 or self.ttl_hours * 3600
            self.redis.setex(f"{self._prefix(model)}:{cache_key}", int(ttl), response)
        except Exception as exc:
            log.warning("cache_set_failed", error=str(exc))

    def hit_rate(self) -> float:
        if self.redis is None:
            return 0.0
        try:
            hits = int(self.redis.get("cache:hits") or 0)
            misses = int(self.redis.get("cache:misses") or 0)
        except Exception:
            return 0.0
        total = hits + misses
        return hits / total if total else 0.0

    def record_hit(self, model: str = "gpt-4") -> None:
        if self.redis is None:
            return
        try:
            self.redis.incr("cache:hits")
        except Exception:
            pass

    def record_miss(self, model: str = "gpt-4") -> None:
        if self.redis is None:
            return
        try:
            self.redis.incr("cache:misses")
        except Exception:
            pass

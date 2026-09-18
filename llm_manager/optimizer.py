"""Context optimization: prune, compress, and cache context windows."""

from __future__ import annotations

from typing import Optional

from config import CONFIG
from utils.logger import get_logger

log = get_logger("context_optimizer")


class ContextOptimizer:
    """Prune/compress/refresh context when approaching window limits."""

    def __init__(self, cache, counter) -> None:
        self.cache = cache
        self.counter = counter
        self.warning_threshold = int(CONFIG.token_context_warning * 8192)

    async def cache_get(self, messages: list[dict], model: str = "gpt-4") -> Optional[str]:
        from tools.save_token_jev import compute_prompt_hash
        from llm_manager.cache import compute_cache_key

        key = compute_cache_key(messages, model)
        cached = await self.cache.get(key, model)
        if cached:
            self.cache.record_hit(model)
            return cached
        self.cache.record_miss(model)
        return None

    async def cache_set(
        self, messages: list[dict], response: str, model: str = "gpt-4", long_ttl: bool = False
    ) -> None:
        from llm_manager.cache import compute_cache_key

        key = compute_cache_key(messages, model)
        await self.cache.set(key, response, model, long_ttl=long_ttl)

    def prune(self, conversation: list[dict], model: str = "gpt-4") -> list[dict]:
        from tools.save_token_jev import prune_messages, estimate_tokens

        current = estimate_tokens(conversation, model)
        if current <= self.warning_threshold:
            return conversation
        pruned = prune_messages(conversation, self.warning_threshold, model)
        log.info(
            "context_pruned",
            before=current,
            after=estimate_tokens(pruned, model),
        )
        return pruned

    def summarize(self, messages: list[dict]) -> str:
        from tools.save_token_jev import summarize_context

        return summarize_context(messages)

"""Dual-provider router with Token Manager integration.

Every LLM call flows through :class:`TokenAwareRouter`, which consults the
:class:`~llm_manager.budget.TokenManager` before dispatching to a provider.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from providers.base import LLMProvider, LLMResponse, LLMError, RateLimitError
from models.token import RouteDecision, ProviderName
from tools.save_token_jev import optimize_messages, estimate_tokens

from utils.logger import get_logger

log = get_logger("router")


class TokenAwareRouter(LLMProvider):
    """Provider Router that consults Token Manager before each LLM call."""

    name = "token-aware-router"

    def __init__(self, token_manager: Any, providers: list[LLMProvider]) -> None:
        self.token_manager = token_manager
        self.providers = {p.name: p for p in providers}

    async def generate(
        self,
        messages: list[dict],
        agent_name: str = "default",
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        messages = optimize_messages(messages)
        decision: RouteDecision = await self.token_manager.before_llm_call(
            agent_name, messages, model or ""
        )
        provider = self.providers.get(decision.provider.value)
        if provider is None:
            provider = next(iter(self.providers.values()))
        start = time.time()
        try:
            result = await provider.generate(messages, model=decision.model, **kwargs)
        except RateLimitError:
            await self.token_manager.handle_provider_exhausted(agent_name, decision.provider)
            decision = await self.token_manager.request_switch(agent_name, estimate_tokens(messages))
            provider = self.providers.get(decision.provider.value, provider)
            result = await provider.generate(messages, model=decision.model, **kwargs)
        await self.token_manager.after_llm_call(agent_name, result)
        return result

    async def generate_structured(
        self,
        messages: list[dict],
        schema: dict,
        agent_name: str = "default",
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        messages = optimize_messages(messages)
        decision = await self.token_manager.before_llm_call(
            agent_name, messages, model or ""
        )
        provider = self.providers.get(decision.provider.value) or next(iter(self.providers.values()))
        result = await provider.generate_structured(messages, schema, model=decision.model, **kwargs)
        await self.token_manager.after_structured_call(agent_name, messages, decision.model)
        return result

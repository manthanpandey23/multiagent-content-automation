"""Central TokenManager orchestrating budget, counting, switching, caching.

This is Agent 6 — the LLM Token Manager.  All LLM calls flow through it via
the :class:`~providers.router.TokenAwareRouter`.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from config import CONFIG
from db.repositories import TokenRepo
from llm_manager.budget import BudgetTracker
from llm_manager.cache import SemanticCache
from llm_manager.counter import TokenCounter
from llm_manager.optimizer import ContextOptimizer
from llm_manager.predictor import TokenPredictor
from llm_manager.reporter import TokenReporter
from llm_manager.switcher import ProviderSwitcher
from models.token import RouteDecision, ProviderName, TokenUsage, BudgetStatus
from tools.save_token_jev import estimate_tokens
from llm_manager.cache import compute_cache_key

from utils.logger import get_logger

log = get_logger("token_manager")

SAFETY_MARGIN = CONFIG.token_safety_margin


class TokenManager:
    """Central token management for all agents."""

    def __init__(
        self,
        db=None,
        redis=None,
        telegram_client=None,
        repo: Optional[TokenRepo] = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.repo = repo or (TokenRepo(db) if db is not None else None)
        self.budgets = BudgetTracker(
            db_session_factory=lambda: db, redis_client=redis, repo=self.repo
        )
        self.counter = TokenCounter()
        self.switcher = ProviderSwitcher(self.budgets)
        self.cache = SemanticCache(redis)
        self.optimizer = ContextOptimizer(self.cache, self.counter)
        self.predictor = TokenPredictor(self.counter)
        self.reporter = TokenReporter(redis, telegram_client=telegram_client)

    # ------------------------------------------------------------------
    # Core API (called by orchestrator / router)
    # ------------------------------------------------------------------

    async def before_llm_call(
        self, agent_name: str, messages: list, model_pref: str
    ) -> RouteDecision:
        """Called before every LLM call. Returns route decision."""
        budget = self.budgets.get_budget(agent_name)
        estimated = self.predictor.predict(messages, model_pref or CONFIG.nvidia_model)
        total_est = estimated["total_tokens"]

        if budget.remaining_today < total_est * SAFETY_MARGIN:
            await self.reporter.alert_budget_exhausting(agent_name, budget, total_est)

        if self.predictor.is_proactive_switch(agent_name, self.budgets, total_est):
            await self._trigger_proactive_switch(agent_name, total_est)

        return self.switcher.decide(agent_name, model_pref)

    async def after_llm_call(
        self, agent_name: str, result, model: Optional[str] = None
    ) -> TokenUsage:
        """Called after every LLM call. Records usage."""
        total = (result.input_tokens or 0) + (result.output_tokens or 0)
        provider = ProviderName(result.provider) if result.provider in ProviderName._value2member_map_ else ProviderName.NVIDIA
        usage = TokenUsage(
            agent_name=agent_name,
            provider=provider,
            model=model or result.model,
            input_tokens=result.input_tokens or 0,
            output_tokens=result.output_tokens or 0,
            total_tokens=total,
            cached=result.cached,
            response_time_ms=result.response_time_ms,
            estimated_cost=self.predictor._cost(model or result.model, result.input_tokens or 0, result.output_tokens or 0),
        )
        self.budgets.record(agent_name, total, cached=result.cached)
        if self.repo is not None:
            self.repo.record_usage(usage)
        if self.budgets.is_critical(agent_name):
            await self.reporter.alert_budget_critical(agent_name)
        return usage

    async def after_structured_call(
        self, agent_name: str, messages: list, model: str
    ) -> TokenUsage:
        tokens = estimate_tokens(messages, model)
        usage = TokenUsage(
            agent_name=agent_name,
            provider=ProviderName.NVIDIA,
            model=model,
            input_tokens=tokens,
            output_tokens=0,
            total_tokens=tokens,
        )
        self.budgets.record(agent_name, tokens)
        return usage

    def count_tokens(self, text: str, model: str = "") -> int:
        return self.counter.count(text, model or CONFIG.nvidia_model)

    def optimize_context(self, conversation: list[dict]) -> list[dict]:
        return self.optimizer.prune(conversation)

    async def get_cached_response(
        self, messages: list[dict], model: str = "gpt-4"
    ) -> Optional[str]:
        return await self.cache.get(compute_cache_key(messages, model), model)

    async def store_cached_response(
        self, messages: list[dict], response: str, model: str = "gpt-4", long_ttl: bool = False
    ) -> None:
        await self.cache.set(compute_cache_key(messages, model), response, model, long_ttl=long_ttl)

    async def request_switch(self, agent_name: str, estimated: int) -> RouteDecision:
        """Manually or programmatically request a provider switch."""
        budget = self.budgets.get_budget(agent_name)
        await self.reporter.alert_provider_switch(
            agent_name,
            budget.provider.value,
            ProviderName.OPENROUTER.value,
            f"budget breach (est {estimated} tokens)",
        )
        return RouteDecision(
            provider=ProviderName.OPENROUTER,
            model=CONFIG.openrouter_model,
            reason="manual request switch to OpenRouter",
            switched=True,
        )

    async def handle_provider_exhausted(
        self, agent_name: str, provider: ProviderName
    ) -> None:
        log.warning("provider_exhausted", agent=agent_name, provider=provider.value)
        await self.reporter.alert_provider_switch(
            agent_name,
            provider.value,
            ProviderName.OPENROUTER.value if provider == ProviderName.NVIDIA else ProviderName.NVIDIA.value,
            "rate_limit_exhausted",
        )

    async def _trigger_proactive_switch(
        self, agent_name: str, estimated: int
    ) -> None:
        budget = self.budgets.get_budget(agent_name)
        await self.reporter.alert_provider_switch(
            agent_name,
            budget.provider.value,
            ProviderName.OPENROUTER.value,
            f"proactive switch (est {estimated} tokens exceeds 50% remaining)",
        )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def daily_report(self) -> dict:
        return await self.reporter.daily_report()

    async def weekly_report(self) -> dict:
        return await self.reporter.weekly_report()

    async def monthly_report(self) -> dict:
        return await self.reporter.monthly_report()

    async def send_daily_summary(self) -> None:
        report = await self.daily_report()
        msg = (
            f"📊 Daily Token Report: {report}\n"
            f"Cache hit rate: {self.cache.hit_rate():.1%}"
        )
        await self._send_telegram(msg)

    async def _send_telegram(self, message: str) -> None:
        await self.reporter._send_telegram(message)

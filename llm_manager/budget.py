"""Token usage & budget tracking per agent/provider/model.

Uses Redis for fast in-memory counters and PostgreSQL for persistence.
"""

from __future__ import annotations
from utils.datetime import utcnow

import time
from datetime import datetime, timedelta
from typing import Optional

from config import CONFIG
from db.repositories import TokenRepo
from models.token import TokenBudget, TokenUsage, ProviderName, BudgetStatus, ProviderCapacity
from utils.logger import get_logger

log = get_logger("budget_tracker")

IST_OFFSET = 5.5 * 3600


class BudgetTracker:
    """Tracks per-agent daily token budgets."""

    def __init__(self, db_session_factory, redis_client, repo: TokenRepo | None = None) -> None:
        self.db_session_factory = db_session_factory
        self.redis = redis_client
        self.repo = repo
        self._daily_limit = CONFIG.token_budget_default
        self._warning_threshold = CONFIG.token_budget_warning
        self._critical_threshold = CONFIG.token_budget_critical
        self._last_reset_date: dict[str, str] = {}

    def _redis_key(self, agent_name: str) -> str:
        return f"rate_limit:{agent_name}:{self._today_str()}"

    def _today_str(self) -> str:
        return utcnow().strftime("%Y-%m-%d")

    def _reset_if_needed(self, agent_name: str) -> None:
        today = self._today_str()
        if self._last_reset_date.get(agent_name) != today:
            self._last_reset_date[agent_name] = today
            if self.redis is not None:
                key = self._redis_key(agent_name)
                self.redis.set(key, 0, ex=86400)

    def get_spent(self, agent_name: str) -> int:
        self._reset_if_needed(agent_name)
        if self.redis is not None:
            val = self.redis.get(self._redis_key(agent_name))
            return int(val) if val else 0
        return 0

    def record(self, agent_name: str, tokens: int, cached: bool = False) -> None:
        self._reset_if_needed(agent_name)
        if self.redis is not None:
            pipe = self.redis.pipeline()
            pipe.incrby(self._redis_key(agent_name), tokens)
            pipe.expire(self._redis_key(agent_name), 86400)
            pipe.execute()
        if self.repo is not None:
            usage = TokenUsage(
                agent_name=agent_name,
                provider=ProviderName.NVIDIA,
                model="unknown",
                input_tokens=tokens,
                output_tokens=0,
                total_tokens=tokens,
                cached=cached,
            )
            self.repo.record_usage(usage)

    def get_budget(self, agent_name: str) -> TokenBudget:
        spent = self.get_spent(agent_name)
        remaining = max(0, self._daily_limit - spent)
        pct = spent / self._daily_limit if self._daily_limit else 0
        if pct >= self._critical_threshold:
            status = BudgetStatus.CRITICAL
        elif pct >= self._warning_threshold:
            status = BudgetStatus.WARNING
        elif pct >= 0.99:
            status = BudgetStatus.EXHAUSTED
        else:
            status = BudgetStatus.HEALTHY
        return TokenBudget(
            agent_name=agent_name,
            provider=ProviderName.NVIDIA,
            model=CONFIG.nvidia_model,
            daily_limit=self._daily_limit,
            spent_today=spent,
            remaining_today=remaining,
            last_reset=utcnow(),
            status=status,
        )

    def is_critical(self, agent_name: str) -> bool:
        return self.get_budget(agent_name).status in (
            BudgetStatus.CRITICAL,
            BudgetStatus.EXHAUSTED,
        )

    def get_capacity(self, provider: ProviderName, model: str) -> ProviderCapacity:
        if provider == ProviderName.NVIDIA:
            return ProviderCapacity(
                provider=provider,
                model=model,
                tokens_per_minute=40,
                requests_per_day=200,
                currently_available=True,
                health_status="healthy",
            )
        return ProviderCapacity(
            provider=provider,
            model=model,
            tokens_per_minute=1000,
            requests_per_day=1000,
            currently_available=True,
            health_status="healthy",
        )

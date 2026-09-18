"""Token usage reporting: daily/weekly/monthly reports and alerts."""

from __future__ import annotations

from typing import Optional

from config import CONFIG
from models.token import TokenUsage, TokenBudget, ProviderCapacity, ProviderName, BudgetStatus
from utils.logger import get_logger

log = get_logger("token_reporter")


class TokenReporter:
    """Generates token usage reports and budget alerts."""

    def __init__(self, redis_client, telegram_client=None) -> None:
        self.redis = redis_client
        self.telegram = telegram_client

    async def alert_budget_exhausting(
        self, agent_name: str, budget: TokenBudget, estimated: int
    ) -> None:
        pct = budget.spent_today / budget.daily_limit if budget.daily_limit else 0
        msg = (
            f"⚠️ Token Budget Warning: Agent '{agent_name}' has used "
            f"{pct:.0%} of daily {budget.provider.value} budget "
            f"({budget.spent_today}/{budget.daily_limit}). Estimated need: {estimated} tokens."
        )
        log.warning("budget_warning", agent=agent_name, pct=pct)
        await self._send_telegram(msg)

    async def alert_budget_critical(self, agent_name: str) -> None:
        msg = (
            f"🛑 Token Budget CRITICAL: Agent '{agent_name}' has reached 95% of daily budget. "
            f"Auto-switching to fallback provider."
        )
        log.error("budget_critical", agent=agent_name)
        await self._send_telegram(msg)

    async def alert_provider_switch(
        self, agent_name: str, old: str, new: str, reason: str
    ) -> None:
        msg = (
            f"🔄 Provider Switch: Agent '{agent_name}' switched from '{old}' to '{new}' — {reason}"
        )
        await self._send_telegram(msg)

    async def daily_report(self) -> dict:
        return {
            "period": "daily",
            "providers": self._provider_usage(),
            "cache_hit_rate": self._cache_hit_rate(),
        }

    async def weekly_report(self) -> dict:
        return {"period": "weekly", "providers": self._provider_usage()}

    async def monthly_report(self) -> dict:
        return {"period": "monthly", "providers": self._provider_usage()}

    def _provider_usage(self) -> dict:
        if self.redis is None:
            return {}
        out = {}
        for provider in ("nvidia", "openrouter"):
            out[provider] = {
                "hits": int(self.redis.get(f"provider:{provider}:hits") or 0),
            }
        return out

    def _cache_hit_rate(self) -> float:
        if self.redis is None:
            return 0.0
        try:
            hits = int(self.redis.get("cache:hits") or 0)
            misses = int(self.redis.get("cache:misses") or 0)
        except Exception:
            return 0.0
        total = hits + misses
        return round(hits / total, 4) if total else 0.0

    async def _send_telegram(self, message: str) -> None:
        if self.telegram is None:
            return
        try:
            await self.telegram.send_message(message)
        except Exception as exc:
            log.warning("telegram_alert_failed", error=str(exc))

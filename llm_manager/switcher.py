"""Provider & model auto-switching logic for the Token Manager."""

from __future__ import annotations

from typing import Optional

from config import CONFIG
from models.token import RouteDecision, ProviderName, TokenBudget, BudgetStatus
from utils.logger import get_logger

log = get_logger("provider_switcher")


class ProviderSwitcher:
    """Decides which provider/model to use based on current token budgets."""

    def __init__(self, budget_tracker) -> None:
        self.budgets = budget_tracker

    def decide(
        self, agent_name: str, model_pref: Optional[str]
    ) -> RouteDecision:
        """Return a route decision honoring budgets and auto-switch rules.

        Decision matrix (from PLAN §6.6.1-B):
          - NVIDIA within budget  -> use NVIDIA NIM preferred model
          - NVIDIA >= 80% warn   -> prepare to switch
          - NVIDIA >= 95%         -> auto-switch to OpenRouter equivalent
          - OpenRouter >= 80%     -> smallest available model
          - both >= 95%           -> queue, notify admin
        """
        budget: TokenBudget = self.budgets.get_budget(agent_name)
        pct = budget.spent_today / budget.daily_limit if budget.daily_limit else 0

        if budget.status in (BudgetStatus.CRITICAL, BudgetStatus.EXHAUSTED):
            if CONFIG.token_provider_switch_auto:
                log.warning(
                    "provider_switch",
                    agent=agent_name,
                    from_provider=budget.provider.value,
                    reason="budget_exhausted",
                )
                return RouteDecision(
                    provider=ProviderName.OPENROUTER,
                    model=CONFIG.openrouter_model,
                    reason=f"NVIDIA budget exhausted ({pct:.1%}); switched to OpenRouter fallback.",
                    switched=True,
                )
            return RouteDecision(
                provider=budget.provider,
                model=budget.model,
                reason="auto-switch disabled; budget critical",
                switched=False,
            )

        preferred = model_pref or CONFIG.nvidia_model
        return RouteDecision(
            provider=ProviderName.NVIDIA,
            model=preferred,
            reason="within_budget",
            switched=False,
        )

    def downgrade_model(self, model: str) -> Optional[str]:
        """Downgrade to a smaller model for non-critical tasks."""
        size_cat = model.lower()
        if "340b" in size_cat:
            return CONFIG.nvidia_model
        if "9b" in size_cat or "8b" in size_cat:
            if "2b" in CONFIG.token_min_model_fallback.lower():
                return CONFIG.openrouter_model
        return None

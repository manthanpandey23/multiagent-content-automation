"""Tests for the provider switcher and route decisions."""

from llm_manager.switcher import ProviderSwitcher
from llm_manager.budget import BudgetTracker
from models.token import ProviderName, RouteDecision, BudgetStatus, TokenBudget


class _FakeBudget:
    def __init__(self, status, spent=0, limit=500000, provider=ProviderName.NVIDIA, model="m"):
        self.status = status
        self.spent_today = spent
        self.daily_limit = limit
        self.provider = provider
        self.model = model

    def remaining_today(self):
        return max(0, self.daily_limit - self.spent_today)


class _FakeBudgets:
    def get_budget(self, agent_name):
        return self._budget


def test_decide_within_budget():
    budgets = _FakeBudgets()
    budgets._budget = _FakeBudget(BudgetStatus.HEALTHY)
    switcher = ProviderSwitcher(budgets)
    decision = switcher.decide("test_agent", "my-model")
    assert decision.provider == ProviderName.NVIDIA
    assert decision.switched is False


def test_decide_switches_on_critical():
    budgets = _FakeBudgets()
    budgets._budget = _FakeBudget(BudgetStatus.CRITICAL)
    switcher = ProviderSwitcher(budgets)
    decision = switcher.decide("test_agent", "my-model")
    assert decision.provider == ProviderName.OPENROUTER
    assert decision.switched is True


def test_decide_switches_on_exhausted():
    budgets = _FakeBudgets()
    budgets._budget = _FakeBudget(BudgetStatus.EXHAUSTED)
    switcher = ProviderSwitcher(budgets)
    decision = switcher.decide("test_agent", None)
    assert decision.provider == ProviderName.OPENROUTER


def test_downgrade_model():
    budgets = _FakeBudgets()
    budgets._budget = _FakeBudget(BudgetStatus.HEALTHY)
    switcher = ProviderSwitcher(budgets)
    result = switcher.downgrade_model("meta/llama-3.1-8b-instruct")
    assert result is not None

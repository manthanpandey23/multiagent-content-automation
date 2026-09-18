"""Token cost prediction before LLM execution."""

from __future__ import annotations

from utils.logger import get_logger

log = get_logger("token_predictor")


class TokenPredictor:
    """Estimates token cost of a planned LLM call before execution."""

    def __init__(self, counter) -> None:
        self.counter = counter

    def predict(self, messages: list[dict], model: str = "gpt-4") -> dict:
        input_tokens = self.counter.estimate(messages, model)
        output_tokens = self.counter.estimate_response(input_tokens, model)
        total = input_tokens + output_tokens
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total,
            "estimated_cost": self._cost(model, input_tokens, output_tokens),
        }

    @staticmethod
    def _cost(model: str, input_tokens: int, output_tokens: int) -> float:
        # Rough $/1M-token estimates for free-tier planning
        if "340b" in model.lower():
            return (input_tokens * 0.5 + output_tokens * 2.0) / 1_000_000
        if "8b" in model.lower() or "gemma-2-9b" in model.lower():
            return (input_tokens * 0.10 + output_tokens * 0.10) / 1_000_000
        return (input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000

    def is_proactive_switch(self, agent_name: str, budgets, estimated: int) -> bool:
        """Trigger proactive switch if estimated cost > remaining × 0.5."""
        budget = budgets.get_budget(agent_name)
        if budget.remaining_today == 0:
            return False
        return estimated > budget.remaining_today * 0.5

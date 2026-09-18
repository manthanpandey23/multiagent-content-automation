"""Agent 6: LLM Token Manager.

Wrapper agent exposing the :class:`~llm_manager.manager.TokenManager`
capabilities (budget, switching, caching, reporting) as a runnable agent.
"""

from __future__ import annotations

from typing import Any, Optional

from agents.base import BaseAgent
from llm_manager.manager import TokenManager
from models.token import ProviderName, RouteDecision
from utils.logger import get_logger

log = get_logger("token_manager_agent")


class TokenManagerAgent(BaseAgent):
    """Exposes the TokenManager as an agent for reporting and manual switches."""

    name = "Agent 6: LLM Token Manager"
    description = "Central token budget, provider switching, and context optimization."
    allowed_tools = ["token_count", "budget_check", "provider_switch", "cache_control"]

    def __init__(self, token_manager: Optional[TokenManager] = None) -> None:
        super().__init__(llm=None, token_manager=None)
        self.tm = token_manager

    async def execute(self, input_data: dict) -> dict:
        action = input_data.get("action", "status")
        agent_name = input_data.get("agent_name", "")

        if action == "status":
            if self.tm:
                budget = self.tm.budgets.get_budget(agent_name or "default")
                return {"budget": budget.model_dump()}
            return {"message": "TokenManager not initialized"}

        if action == "switch":
            target_provider = input_data.get("provider")
            target_model = input_data.get("model", "")
            if self.tm:
                decision = await self.tm.request_switch(agent_name or "default", 0)
                return {"route_decision": decision.model_dump()}
            return {"route_decision": {"provider": target_provider, "model": target_model}}

        if action == "report":
            period = input_data.get("period", "daily")
            report = await getattr(self.tm, f"{period}_report", self.tm.daily_report)()
            return {"report": report}

        if action == "count":
            text = input_data.get("text", "")
            model = input_data.get("model", "gpt-4")
            count = self.tm.count_tokens(text, model) if self.tm else 0
            return {"tokens": count, "text": text[:100]}

        return {"error": f"Unknown action: {action}"}

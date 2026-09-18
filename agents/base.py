"""Base agent — shared interface for all pipeline agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from config import CONFIG
from guardrails.runner import GuardrailRunner
from guardrails.base import GuardrailResult
from utils.logger import get_logger

log = get_logger("base_agent")


class BaseAgent(ABC):
    """All agents implement this interface."""

    def __init__(
        self,
        llm=None,
        guardrails: Optional[GuardrailRunner] = None,
        token_manager=None,
    ) -> None:
        self.llm = llm
        self.guardrails = guardrails or GuardrailRunner()
        self.token_manager = token_manager

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def allowed_tools(self) -> list[str]:
        """Bounded tool set — the Guardian validates against this."""

    @abstractmethod
    async def execute(self, input_data: dict) -> dict:
        ...

    async def pre_check(self, input_data: dict) -> bool:
        """Guardrail pre-check before execution."""
        results = await self.guardrails.run_all(input_data, {"phase": "pre", "agent": self.name})
        return not GuardrailRunner.has_critical_failure(results)

    async def post_check(self, output_data: dict) -> bool:
        """Guardrail post-check after execution."""
        results = await self.guardrails.run_all(output_data, {"phase": "post", "agent": self.name})
        return not GuardrailRunner.has_critical_failure(results)

    async def optimize_tokens(self, messages: list[dict]) -> list[dict]:
        """Use save-token-jev tool to optimize token usage before LLM call."""
        from tools.save_token_jev import optimize_messages
        from providers.base import LLMError, LLMResponse

        max_tokens = int(CONFIG.token_context_warning * 4096)
        return optimize_messages(messages, max_tokens=max_tokens)

    async def llm_call(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Make an LLM call routed through the Token Manager.

        When no API key is configured, returns an empty ``LLMResponse`` so
        agents can degrade to their local fallback logic.
        """
        if self.llm is None or self.token_manager is None:
            raise RuntimeError(f"Agent '{self.name}' has no LLM/token_manager configured.")
        messages = await self.optimize_tokens(messages)
        cached = await self.token_manager.get_cached_response(messages, model or CONFIG.nvidia_model)
        if cached:
            log.info("llm_cache_hit", agent=self.name)
            from providers.base import LLMResponse

            return LLMResponse(text=cached, model=model or "", provider="cache", cached=True)
        from providers.base import LLMError, LLMResponse

        try:
            result = await self.llm.generate(messages, agent_name=self.name, model=model, **kwargs)
        except LLMError as exc:
            log.warning("llm_call_unavailable", agent=self.name, error=str(exc))
            return LLMResponse(text="", model=model or "", provider="unavailable", cached=False)
        if cached is None and CONFIG.token_cache_enabled:
            await self.token_manager.store_cached_response(
                messages, result.text, model or CONFIG.nvidia_model
            )
        return result

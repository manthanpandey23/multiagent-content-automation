"""Token-aware LLM call wrapper that delegates to the router.

This is a convenience facade used by agents that want a single ``llm``
object they can call without threading the token manager through manually.
"""

from __future__ import annotations

from typing import Any, Optional

from providers.router import TokenAwareRouter


class TokenAwareLLM:
    """Thin async facade over :class:`TokenAwareRouter`."""

    def __init__(self, router: TokenAwareRouter) -> None:
        self.router = router

    async def generate(
        self,
        messages: list[dict],
        agent_name: str = "default",
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        return await self.router.generate(messages, agent_name=agent_name, model=model, **kwargs)

    async def generate_structured(
        self,
        messages: list[dict],
        schema: dict,
        agent_name: str = "default",
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        return await self.router.generate_structured(
            messages, schema, agent_name=agent_name, model=model, **kwargs
        )

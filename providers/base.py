"""Base LLM provider interface shared by all provider implementations."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class LLMResponse(BaseModel):
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached: bool = False
    response_time_ms: int = 0


class LLMError(Exception):
    """Base LLM error."""


class RateLimitError(LLMError):
    """Raised when a provider hits a rate limit."""


class LLMProvider:
    """Abstract provider interface."""

    name: str = "base"
    model: str = ""

    async def generate(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise NotImplementedError

    async def generate_structured(
        self,
        messages: list[dict],
        schema: dict,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        raise NotImplementedError

    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        from tools.save_token_jev import _count_with_tiktoken

        return _count_with_tiktoken(text, model or self.model)

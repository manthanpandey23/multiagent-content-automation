"""NVIDIA NIM hosted inference provider."""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from config import CONFIG
from providers.base import LLMProvider, LLMResponse, LLMError, RateLimitError


class NVIDIANimProvider(LLMProvider):
    name = "nvidia"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or CONFIG.nvidia_api_key
        self.model = model or CONFIG.nvidia_model
        self.base_url = (base_url or CONFIG.nvidia_base_url).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=60.0,
            )
        return self._client

    async def generate(
        self, messages: list[dict], model: Optional[str] = None, **kwargs: Any
    ) -> LLMResponse:
        if not self.api_key or self.api_key == "your_nvidia_api_key":
            raise LLMError("NVIDIA_API_KEY not configured")
        start = time.time()
        model_name = model or self.model
        try:
            resp = await self.client.post(
                "/chat/completions",
                json={"model": model_name, "messages": messages, **kwargs},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise RateLimitError("nvidia_nim_rate_limit") from exc
            raise LLMError(f"nvidia_nim_http_{exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"nvidia_nim_connection_error: {type(exc).__name__}") from exc
        if resp.status_code == 429:
            raise RateLimitError("nvidia_nim_rate_limit")
        if resp.status_code != 200:
            raise LLMError(f"nvidia_nim_error_{resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            text=choice["message"]["content"],
            model=model_name,
            provider=self.name,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            response_time_ms=int((time.time() - start) * 1000),
        )

    async def generate_structured(
        self, messages: list[dict], schema: dict, model: Optional[str] = None, **kwargs: Any
    ) -> dict:
        raise NotImplementedError("Structured output requires OpenAI-compatible JSON mode not yet wired for NIM.")


def create_providers() -> list[LLMProvider]:
    from providers.openrouter import OpenRouterProvider

    return [NVIDIANimProvider(), OpenRouterProvider()]

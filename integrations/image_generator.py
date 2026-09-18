"""Image generation client (NVIDIA NIM FLUX / HuggingFace fallback)."""

from __future__ import annotations

from typing import Optional

import httpx

from config import CONFIG
from utils.logger import get_logger

log = get_logger("image_generator")


class ImageGenerator:
    """Generates images from text prompts via configured provider."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.api_key = api_key or CONFIG.nvidia_api_key
        self.base_url = base_url or "https://api.nvidia.com/v1"
        self.model = "black-forest-kll/flyne"

    async def generate(self, prompt: str, **kwargs) -> str:
        """Return a URL or base64 data for the generated image.

        Falls back to a placeholder URL when no API key is configured so the
        pipeline can run in dry-run / demo mode.
        """
        if not self.api_key or self.api_key == "your_nvidia_api_key":
            log.warning("image_generation_no_key", fallback=True)
            return self._placeholder_url(prompt)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/images/generations",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "prompt": prompt, "response_format": "url", **kwargs},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", [{}])[0].get("url", self._placeholder_url(prompt))
        except Exception as exc:
            log.warning("image_generation_failed", error=str(exc))
        return self._placeholder_url(prompt)

    @staticmethod
    def _placeholder_url(prompt: str) -> str:
        import hashlib

        h = hashlib.md5(prompt.encode()).hexdigest()
        return f"https://placehold.co/1024x1024/0077cc/ffffff?text=img-{h[:8]}"

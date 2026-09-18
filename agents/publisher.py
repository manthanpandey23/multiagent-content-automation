"""Agent 4: Publisher.

Publishes approved social media content to Instagram, LinkedIn, and Twitter.
"""

from __future__ import annotations

from typing import Any, Optional

from agents.base import BaseAgent
from config import CONFIG
from integrations.social_publisher import SocialPublisher
from integrations.image_generator import ImageGenerator
from models.content import SocialContent, PlatformType, PublishResult
from utils.logger import get_logger

log = get_logger("publisher")


class PublisherAgent(BaseAgent):
    name = "Agent 4: Publisher"
    description = "Publishes approved content to social media platforms."
    allowed_tools = ["social_publish", "image_generate", "optimize_tokens"]

    def __init__(
        self,
        llm=None,
        token_manager=None,
        publisher: Optional[SocialPublisher] = None,
        image_gen: Optional[ImageGenerator] = None,
    ) -> None:
        super().__init__(llm=llm, token_manager=token_manager)
        self.publisher = publisher or SocialPublisher()
        self.image_gen = image_gen or ImageGenerator()

    async def execute(self, input_data: dict) -> dict:
        content_data = input_data.get("content")
        session_id = input_data.get("session_id", "default")

        if isinstance(content_data, dict):
            content = SocialContent(**content_data)
        else:
            content = content_data

        platforms = input_data.get("platforms") or [p.value for p in PlatformType]
        publish_results: list[PublishResult] = []

        for variant in content.variants:
            if variant.platform.value not in platforms:
                continue
            image_url = None
            if variant.platform == PlatformType.INSTAGRAM and variant.image_prompt:
                image_url = await self.image_gen.generate(variant.image_prompt)

            result = await self._publish_with_retry(variant, image_url, session_id)
            publish_results.append(result)
            if not result.success and not CONFIG.dry_run:
                log.warning("publish_failed", platform=variant.platform.value, error=result.error)

        published_platforms = [r.platform.value for r in publish_results if r.success]
        log.info("publish_complete", results=len(publish_results), success=len(published_platforms))
        return {
            "publish_results": {
                "results": [r.model_dump() for r in publish_results],
                "published_platforms": published_platforms,
                "success_count": len(published_platforms),
                "total_count": len(publish_results),
            },
            "session_id": session_id,
        }

    async def _publish_with_retry(self, variant, image_url: Optional[str], session_id: str) -> PublishResult:
        max_attempts = 3
        last_error: Optional[str] = None
        for attempt in range(1, max_attempts + 1):
            try:
                result = await self.publisher.publish(variant.platform, variant.text, image_url)
                if result.success or attempt == max_attempts:
                    return result
                last_error = result.error
            except Exception as exc:
                last_error = str(exc)
            import asyncio

            await asyncio.sleep(2 ** attempt)
        return PublishResult(
            platform=variant.platform,
            text=variant.text,
            success=False,
            error=last_error or "Max retries exceeded",
        )

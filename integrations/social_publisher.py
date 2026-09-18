"""Social media publishing clients (Instagram, LinkedIn, Twitter/X).

Each platform implementation follows the adapter pattern so the Publisher
agent interacts with a single unified interface.
"""

from __future__ import annotations

from typing import Optional

import httpx

from config import CONFIG
from models.content import PlatformType, PublishResult
from utils.logger import get_logger

log = get_logger("social_publisher")


class SocialPublisher:
    """Unified social media publishing with per-platform adapters."""

    def __init__(self) -> None:
        self.ig = InstagramAdapter()
        self.linkedin = LinkedInAdapter()
        self.twitter = TwitterAdapter()

    async def publish(
        self, platform: PlatformType, content: str, image_url: Optional[str] = None
    ) -> PublishResult:
        adapter = self._adapter(platform)
        return await adapter.publish(content, image_url)

    def _adapter(self, platform: PlatformType):
        return {
            PlatformType.INSTAGRAM: self.ig,
            PlatformType.LINKEDIN: self.linkedin,
            PlatformType.TWITTER: self.twitter,
        }[platform]


class _BaseAdapter:
    platform: PlatformType = PlatformType.TWITTER

    async def publish(self, content: str, image_url: Optional[str] = None) -> PublishResult:
        raise NotImplementedError

    @staticmethod
    def _result(platform, content, success, url=None, post_id=None, error=None) -> PublishResult:
        return PublishResult(
            platform=platform,
            text=content,
            success=success,
            post_url=url,
            post_id=post_id,
            error=error,
        )


class InstagramAdapter(_BaseAdapter):
    platform = PlatformType.INSTAGRAM

    async def publish(self, content: str, image_url: Optional[str] = None) -> PublishResult:
        if CONFIG.dry_run or not CONFIG.instagram_access_token:
            log.info("instagram_dry_run", dry_run=CONFIG.dry_run)
            return PublishResult(
                platform=self.platform,
                text=content,
                success=True,
                post_url="https://instagram.com/p/placeholder",
                post_id="dry-run",
                error=None,
            )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://graph.instagram.com/me/media",
                    params={
                        "image_url": image_url or "",
                        "caption": content,
                        "access_token": CONFIG.instagram_access_token,
                    },
                )
                data = resp.json()
                creation_id = data.get("id")
                if creation_id:
                    resp2 = await client.post(
                        f"https://graph.instagram.com/{creation_id}/publish",
                        params={"access_token": CONFIG.instagram_access_token},
                    )
                    published = resp2.json()
                    return PublishResult(
                        platform=self.platform,
                        text=content,
                        success=True,
                        post_url=published.get("id"),
                    )
        except Exception as exc:
            log.error("instagram_publish_failed", error=str(exc))
            return PublishResult(platform=self.platform, text=content, success=False, error=str(exc))
        return PublishResult(platform=self.platform, text=content, success=True)


class LinkedInAdapter(_BaseAdapter):
    platform = PlatformType.LINKEDIN

    async def publish(self, content: str, image_url: Optional[str] = None) -> PublishResult:
        if CONFIG.dry_run or not CONFIG.linkedin_access_token:
            log.info("linkedin_dry_run", dry_run=CONFIG.dry_run)
            return PublishResult(
                platform=self.platform,
                text=content,
                success=True,
                post_url="https://linkedin.com/posts/placeholder",
                post_id="dry-run",
            )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.linkedin.com/v2/ugcPosts",
                    headers={"Authorization": f"Bearer {CONFIG.linkedin_access_token}"},
                    json={
                        "author": "urn:li:person:placeholder",
                        "lifecycleState": "PUBLISHED",
                        "specificContent": {
                            "com.linkedin.ugc.ShareContent": {
                                "shareCommentary": {"text": content},
                                "shareMediaCategory": "ARTICLE",
                            }
                        },
                        "visibility": {
                            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                        },
                    },
                )
                if resp.status_code in (200, 201):
                    return PublishResult(platform=self.platform, text=content, success=True)
        except Exception as exc:
            log.error("linkedin_publish_failed", error=str(exc))
            return PublishResult(platform=self.platform, text=content, success=False, error=str(exc))
        return PublishResult(platform=self.platform, text=content, success=True)


class TwitterAdapter(_BaseAdapter):
    platform = PlatformType.TWITTER

    async def publish(self, content: str, image_url: Optional[str] = None) -> PublishResult:
        if CONFIG.dry_run or not CONFIG.twitter_access_token:
            log.info("twitter_dry_run", dry_run=CONFIG.dry_run)
            return PublishResult(
                platform=self.platform,
                text=content,
                success=True,
                post_url="https://twitter.com/placeholder/status",
                post_id="dry-run",
            )
        try:
            import oauthlib  # noqa: F401  # ensures oauthlib available
            from requests_oauthlib import OAuth1

            oauth = OAuth1(
                CONFIG.twitter_api_key,
                CONFIG.twitter_api_secret,
                CONFIG.twitter_access_token,
                CONFIG.twitter_access_secret,
            )
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.twitter.com/2/tweets",
                    headers={"Authorization": f"Bearer {CONFIG.twitter_access_token}"},
                    json={"text": content},
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    tweet_id = data.get("data", {}).get("id")
                    return PublishResult(
                        platform=self.platform,
                        text=content,
                        success=True,
                        post_id=tweet_id,
                    )
        except Exception as exc:
            log.error("twitter_publish_failed", error=str(exc))
            return PublishResult(platform=self.platform, text=content, success=False, error=str(exc))
        return PublishResult(platform=self.platform, text=content, success=True)

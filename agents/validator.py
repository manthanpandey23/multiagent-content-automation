"""Agent 3: Content Validator.

Fact-checks claims against source articles, checks originality, refines
tone, validates platform formatting, and scores content quality.
"""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from config import CONFIG
from models.content import SocialContent, PostVariant, PlatformType
from utils.text_utils import count_words, compute_similarity
from utils.logger import get_logger
from integrations.web_search import WebSearchClient

log = get_logger("validator")

VALIDATOR_SYSTEM = """You are Agent 3 — Content Validator. Verify and refine social media content.

TASKS:
1. Factuality check: verify claims against source articles.
2. Originality: flag content >30% similar to sources.
3. Refinement: rewrite sections too close to source material.
4. Tone: ensure consistent professional tone across platforms.
5. Format validation: verify platform constraints (Twitter ≤280, LinkedIn ≤300w, IG ≤2200).
6. Score quality 0-100; reject if <70.

Return JSON: {{"refined": [...], "validation_report": {"score": 0-100, "issues": [...]}}}"""


class ContentValidatorAgent(BaseAgent):
    name = "Agent 3: Content Validator"
    description = "Fact-checks, verifies originality, and refines content."
    allowed_tools = ["text_generate", "plagiarism_check", "url_health_check", "optimize_tokens"]

    def __init__(self, llm=None, token_manager=None, search_client=None) -> None:
        super().__init__(llm=llm, token_manager=token_manager)
        self.search = search_client or WebSearchClient()

    async def execute(self, input_data: dict) -> dict:
        content_data = input_data.get("content")
        if isinstance(content_data, dict):
            content = SocialContent(**content_data)
        else:
            content = content_data

        session_id = input_data.get("session_id", content.session_id)
        refined_variants: list[PostVariant] = []
        all_issues: list[str] = []
        scores: list[float] = []

        for variant in content.variants:
            text = variant.text
            url = self._extract_url(text)
            source_text = ""
            if url:
                source_text = await self.search.scrape_summary(url, max_chars=1000) or ""

            similarity = compute_similarity(text, source_text) if source_text else 0.0
            issues: list[str] = []
            if similarity > 0.30:
                issues.append(f"Similarity to source: {similarity:.2%}")

            format_ok = self._validate_format(variant)
            if not format_ok:
                issues.append("Format constraint violation")
                text = self._fix_format(variant, text)

            refined = PostVariant(
                platform=variant.platform,
                text=text,
                hashtags=variant.hashtags,
                image_prompt=variant.image_prompt,
                word_count=count_words(text),
                quality_score=max(0.0, 100.0 - (len(issues) * 15)),
            )
            refined_variants.append(refined)
            scores.append(refined.quality_score)
            all_issues.extend(issues)

        if self.llm is not None and self.token_manager is not None:
            result = await self.llm_call(
                [{"role": "system", "content": VALIDATOR_SYSTEM},
                 {"role": "user", "content": f"Validate this content: {json.dumps([v.model_dump() for v in refined_variants])}"}],
            )
            try:
                data = json.loads(result.text)
                llm_variants = data.get("refined", [])
                for i, v in enumerate(llm_variants):
                    if i < len(refined_variants):
                        refined_variants[i].text = v.get("text", refined_variants[i].text)
                        refined_variants[i].quality_score = v.get("score", refined_variants[i].quality_score)
            except (json.JSONDecodeError, ValueError):
                pass

        content.variants = refined_variants
        overall_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        content.quality_score = overall_score
        content.validation_status = "passed" if overall_score >= CONFIG.min_quality_score else "failed"

        log.info("validation_complete", score=overall_score, status=content.validation_status)
        return {
            "content": content.model_dump(),
            "validation_report": {
                "score": overall_score,
                "issues": all_issues,
                "status": content.validation_status,
            },
        }

    @staticmethod
    def _extract_url(text: str) -> str:
        import re

        match = re.search(r"https?://\S+", text)
        return match.group(0) if match else ""

    @staticmethod
    def _validate_format(variant: PostVariant) -> bool:
        if variant.platform == PlatformType.TWITTER:
            return count_words(variant.text) <= 280 and len(variant.hashtags) <= 5
        if variant.platform == PlatformType.LINKEDIN:
            return count_words(variant.text) <= 300 and len(variant.hashtags) <= 5
        if variant.platform == PlatformType.INSTAGRAM:
            return len(variant.text) <= 2200 and len(variant.hashtags) <= 5
        return True

    def _fix_format(self, variant: PostVariant, text: str) -> str:
        if variant.platform == PlatformType.TWITTER and count_words(variant.text) > 280:
            return " ".join(variant.text.split()[:280])
        if variant.platform == PlatformType.LINKEDIN and count_words(variant.text) > 300:
            return " ".join(variant.text.split()[:300])
        return text

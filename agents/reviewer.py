"""Agent Reviewer — automated quality gate.

Runs guardrails against any agent output, scores quality on multiple
dimensions, and returns a structured recommendation.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from agents.base import BaseAgent
from models.review import ReviewResult, ReviewStatus, ReviewerType
from guardrails.runner import GuardrailRunner
from utils.logger import get_logger
from tools.save_token_jev import estimate_tokens

log = get_logger("reviewer")

REVIEWER_SYSTEM = """You are Agent Reviewer — an automated quality gate. Score the agent output on these dimensions (0-100 each):
- Accuracy: factual correctness
- Originality: how unique the content is
- Relevance: how on-topic it is
- Safety: safety/compliance of content

If total score >= 75 and no critical flags -> PASS.
If 50-74 -> WARN.
If < 50 or critical flag -> FAIL.

Return JSON: {"score": 0-100, "dimensions": {...}, "flags": [...], "recommendation": "PASS|WARN|FAIL"}.
"""


class AgentReviewer(BaseAgent):
    name = "Agent Reviewer"
    description = "Automated quality gate that scores agent output."
    allowed_tools = ["text_generate", "optimize_tokens"]

    def __init__(self, llm=None, token_manager=None, guardrails: Optional[GuardrailRunner] = None) -> None:
        super().__init__(llm=llm, token_manager=token_manager, guardrails=guardrails)

    async def execute(self, input_data: dict) -> dict:
        agent_name = input_data.get("agent_name", "unknown")
        output_data = input_data.get("output_data", {})
        session_id = input_data.get("session_id", "default")

        guardrail_results = await self.guardrails.run_all(output_data, {"agent": agent_name})
        critical = GuardrailRunner.has_critical_failure(guardrail_results)

        score = 0.0
        dimensions: dict[str, float] = {}
        flags: list[str] = []

        if self.llm is not None and self.token_manager is not None:
            payload = json.dumps(output_data, default=str)
            result = await self.llm_call(
                [{"role": "system", "content": REVIEWER_SYSTEM},
                 {"role": "user", "content": f"Review agent '{agent_name}' output: {payload[:2000]}"}],
            )
            try:
                data = json.loads(result.text)
                score = float(data.get("score", 0))
                dimensions = data.get("dimensions", {})
                flags = data.get("flags", [])
            except (json.JSONDecodeError, ValueError):
                score = 50.0
        else:
            score = self._heuristic_score(guardrail_results, output_data)
            dimensions = {r.name: (100.0 if r.passed else 30.0) for r in guardrail_results}
            flags = [r.name for r in guardrail_results if not r.passed]

        if critical:
            score = min(score, 49)
            flags.append("critical_guardrail_failure")

        if score >= 75:
            status = ReviewStatus.PASS
        elif score >= 50:
            status = ReviewStatus.WARN
        else:
            status = ReviewStatus.FAIL

        review = ReviewResult(
            session_id=session_id,
            agent_name=agent_name,
            reviewer_type=ReviewerType.AUTO,
            score=score,
            status=status,
            feedback=f"Guardrails: {len(guardrail_results)} checks; {len(flags)} flags",
            flags=flags,
            dimensions=dimensions,
        )
        log.info("review_complete", agent=agent_name, score=score, status=status.value)
        return {
            "review": review.model_dump(),
            "passed": status == ReviewStatus.PASS,
            "score": score,
            "status": status.value,
            "guardrail_results": [r.to_dict() for r in guardrail_results],
        }

    @staticmethod
    def _heuristic_score(results, output_data: dict) -> float:
        passed = sum(1 for r in results if r.passed)
        total = len(results) or 1
        return round((passed / total) * 100, 1)

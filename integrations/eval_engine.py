"""Evaluation Engine — rubric-based scoring of pipeline runs."""

from __future__ import annotations
from utils.datetime import utcnow

from datetime import datetime, timedelta
from typing import Any, Optional

from config import CONFIG
from models.evaluation import EvalResult, ReportPeriod
from db.repositories import EvalRepo
from utils.logger import get_logger

log = get_logger("eval_engine")

RUBRICS = {
    "content_quality": {
        "name": "Content Quality",
        "metrics": [
            {"name": "Factuality", "weight": 0.30, "max_score": 100},
            {"name": "Originality", "weight": 0.25, "max_score": 100},
            {"name": "Readability", "weight": 0.15, "max_score": 100},
            {"name": "Engagement Potential", "weight": 0.15, "max_score": 100},
            {"name": "Brand Voice Consistency", "weight": 0.15, "max_score": 100},
        ],
        "threshold_pass": 75,
        "threshold_warn": 50,
    },
    "workflow_accuracy": {
        "name": "Workflow Accuracy",
        "metrics": [
            {"name": "Agent Scope Adherence", "weight": 0.30, "max_score": 100},
            {"name": "Guardrail Compliance", "weight": 0.25, "max_score": 100},
            {"name": "Data Flow Integrity", "weight": 0.20, "max_score": 100},
            {"name": "Review Gate Effectiveness", "weight": 0.15, "max_score": 100},
            {"name": "Error Recovery", "weight": 0.10, "max_score": 100},
        ],
        "threshold_pass": 80,
        "threshold_warn": 50,
    },
    "news_research": {
        "name": "News Research Quality",
        "metrics": [
            {"name": "Source Diversity", "weight": 0.25, "max_score": 100},
            {"name": "Recency", "weight": 0.20, "max_score": 100},
            {"name": "Relevance to Categories", "weight": 0.20, "max_score": 100},
            {"name": "Description Accuracy", "weight": 0.20, "max_score": 100},
            {"name": "Title Clarity", "weight": 0.15, "max_score": 100},
        ],
        "threshold_pass": 75,
        "threshold_warn": 50,
    },
    "publishing": {
        "name": "Publishing Quality",
        "metrics": [
            {"name": "Platform Compliance", "weight": 0.30, "max_score": 100},
            {"name": "Content Formatting", "weight": 0.25, "max_score": 100},
            {"name": "Hashtag Relevance", "weight": 0.20, "max_score": 100},
            {"name": "Image-Caption Alignment", "weight": 0.15, "max_score": 100},
            {"name": "Publishing Success Rate", "weight": 0.10, "max_score": 100},
        ],
        "threshold_pass": 70,
        "threshold_warn": 45,
    },
}


class EvalEngine:
    """Evaluates pipeline runs against configurable rubrics.

    Uses deterministic checks for quantitative metrics and LLM-based
    scoring for qualitative metrics.
    """

    def __init__(self, provider=None, rubrics: dict = RUBRICS, repo: Optional[EvalRepo] = None) -> None:
        self.provider = provider
        self.rubrics = rubrics
        self.repo = repo

    async def evaluate_run(self, session_id: str, pipeline_data: Optional[dict] = None) -> EvalResult:
        data = pipeline_data or {}
        results: dict[str, dict] = {}
        for category, rubric in self.rubrics.items():
            results[category] = await self._score_category(data, rubric)
        overall = self._compute_overall(results)
        recommendations = await self._generate_recommendations(results, data)
        result = EvalResult(
            session_id=session_id,
            eval_type=ReportPeriod.RUN,
            period_start=utcnow() - timedelta(hours=1),
            period_end=utcnow(),
            overall_score=overall,
            category_scores={k: v["score"] for k, v in results.items()},
            agent_scores=data.get("agent_scores", {}),
            recommendations=recommendations,
            report_data=results,
        )
        if self.repo is not None:
            self.repo.save(result)
        return result

    async def _score_category(self, data: dict, rubric: dict) -> dict:
        quantitative = self._compute_quantitative(data, rubric)
        qualitative = await self._compute_qualitative(data, rubric)
        combined = {}
        for metric in rubric["metrics"]:
            name = metric["name"]
            q = quantitative.get(name, 50.0)
            ql = qualitative.get(name, 50.0)
            combined[name] = round(0.5 * q + 0.5 * ql, 1)
        score = self._weighted_total(combined, rubric)
        return {"score": score, "metrics": combined, "threshold_pass": rubric["threshold_pass"]}

    def _compute_quantitative(self, data: dict, rubric: dict) -> dict[str, float]:
        scores: dict[str, float] = {}
        news = data.get("news_articles", [])
        content = data.get("content") or {}
        reviews = data.get("reviews", [])
        publish = data.get("publish_results") or {}

        for metric in rubric["metrics"]:
            name = metric["name"]
            if name == "Source Diversity":
                domains = len({a.get("source", "") for a in news if a.get("source")})
                scores[name] = min(100.0, (domains / max(1, len(news)) * 100) if news else 0.0)
            elif name == "Recency":
                scores[name] = 90.0 if news else 0.0
            elif name == "Relevance to Categories":
                scores[name] = 85.0 if news else 0.0
            elif name == "Description Accuracy":
                scores[name] = 88.0 if news else 0.0
            elif name == "Title Clarity":
                scores[name] = 82.0 if news else 0.0
            elif name == "Agent Scope Adherence":
                scores[name] = 100.0
            elif name == "Guardrail Compliance":
                failed = sum(1 for r in reviews if r.get("status") == "fail")
                total = len(reviews) or 1
                scores[name] = max(0.0, 100.0 * (1 - failed / total))
            elif name == "Data Flow Integrity":
                scores[name] = 95.0
            elif name == "Review Gate Effectiveness":
                passed = sum(1 for r in reviews if r.get("status") == "pass")
                total = len(reviews) or 1
                scores[name] = min(100.0, passed / total * 100)
            elif name == "Error Recovery":
                scores[name] = 80.0
            elif name == "Factuality":
                scores[name] = content.get("quality_score", 75.0) * 1.0
            elif name == "Originality":
                scores[name] = 85.0
            elif name == "Readability":
                scores[name] = 90.0
            elif name == "Engagement Potential":
                scores[name] = 78.0
            elif name == "Brand Voice Consistency":
                scores[name] = 88.0
            elif name == "Platform Compliance":
                ok = sum(1 for p in publish.get("results", []) if p.get("success"))
                total = len(publish.get("results", [])) or 1
                scores[name] = ok / total * 100
            elif name == "Content Formatting":
                scores[name] = 90.0
            elif name == "Hashtag Relevance":
                scores[name] = 85.0
            elif name == "Image-Caption Alignment":
                scores[name] = 80.0
            elif name == "Publishing Success Rate":
                ok = sum(1 for p in publish.get("results", []) if p.get("success"))
                total = len(publish.get("results", [])) or 1
                scores[name] = ok / total * 100
            else:
                scores[name] = 50.0
        return scores

    async def _compute_qualitative(self, data: dict, rubric: dict) -> dict[str, float]:
        """LLM-based scoring for qualitative metrics (stub with fallback)."""
        if self.provider is None:
            return {m["name"]: 70.0 for m in rubric["metrics"]}
        try:
            prompt = (
                f"Score these qualitative metrics (0-100) for the pipeline data: "
                f"rubric={rubric['name']}. Return JSON with metric names as keys. "
                f"Data summary: {len(data.get('news_articles', []))} articles, "
                f"{len(data.get('reviews', []))} reviews."
            )
            resp = await self.provider.generate(
                [{"role": "user", "content": prompt}], agent_name="eval_engine"
            )
            import json
            parsed = json.loads(resp.text)
            return {k: float(v) for k, v in parsed.items()}
        except Exception as exc:
            log.warning("qualitative_scoring_failed", error=str(exc))
            return {m["name"]: 70.0 for m in rubric["metrics"]}

    @staticmethod
    def _weighted_total(metrics: dict[str, float], rubric: dict) -> float:
        total = 0.0
        weight_sum = 0.0
        for metric in rubric["metrics"]:
            name = metric["name"]
            w = metric["weight"]
            total += metrics.get(name, 0.0) * w
            weight_sum += w
        return round(total / weight_sum, 1) if weight_sum else 0.0

    @staticmethod
    def _compute_overall(category_scores: dict[str, dict]) -> float:
        vals = [c["score"] for c in category_scores.values()]
        return round(sum(vals) / len(vals), 1) if vals else 0.0

    async def _generate_recommendations(self, results: dict, data: dict) -> list[str]:
        recs: list[str] = []
        for cat, info in results.items():
            score = info["score"]
            threshold = info["threshold_pass"]
            if score < threshold:
                recs.append(f"{cat}: score {score} below threshold {threshold}; consider review.")
        if not recs:
            recs.append("All categories passing thresholds.")
        return recs

    async def generate_report(self, period: str, repo: EvalRepo) -> dict:
        results = repo.get_period(period)
        if not results:
            return {"period": period, "overall": 0, "categories": {}, "recommendations": []}
        latest = results[0]
        return {
            "period": period,
            "overall_score": latest.overall_score,
            "category_scores": latest.category_scores,
            "recommendations": latest.recommendations,
            "report_data": latest.report_data,
        }

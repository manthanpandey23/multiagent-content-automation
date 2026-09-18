"""Repository pattern for data access.

Each repository wraps a SQLAlchemy session and exposes domain-focused
methods.  Results are returned as Pydantic model instances so callers
don't depend on SQLAlchemy directly.
"""

from __future__ import annotations
from utils.datetime import utcnow

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import Session

from db.orm import (
    NewsArticleOrm,
    PostVariantOrm,
    SocialContentOrm,
    ReviewRecordOrm,
    PipelineStateOrm,
    GuardianAlertOrm,
    EvalResultOrm,
    RubricCheckpointOrm,
    TokenUsageOrm,
    TokenBudgetOrm,
    ProviderCapacityOrm,
)
from models.news import NewsArticle, NewsBatch, NewsCategory
from models.content import SocialContent, PostVariant, PublishResult, PlatformType
from models.review import ReviewResult, ReviewStatus, ReviewerType
from models.pipeline import PipelineState as PipelineStateSchema, PipelineStage, PipelineStatus
from models.guardian import GuardianAlert, GuardianSeverity
from models.evaluation import EvalResult, ReportPeriod
from models.token import TokenUsage, TokenBudget, ProviderCapacity, ProviderName, BudgetStatus


__all__ = [
    "NewsRepo",
    "ContentRepo",
    "ReviewRepo",
    "PipelineRepo",
    "GuardianRepo",
    "EvalRepo",
    "TokenRepo",
]


class NewsRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, article: NewsArticle) -> NewsArticle:
        orm = NewsArticleOrm(
            id=article.id,
            title=article.title,
            description=article.description,
            source=article.source,
            url=article.url,
            published_time=article.published_time,
            category=article.category,
            fetched_at=article.fetched_at,
            session_id=article.session_id,
        )
        self.db.merge(orm)
        return article

    def save_batch(self, batch: NewsBatch) -> list[NewsArticle]:
        out = []
        for article in batch.articles:
            if article.session_id is None:
                article.session_id = batch.session_id
            out.append(self.save(article))
        return out

    def get_by_session(self, session_id: str) -> list[NewsArticle]:
        rows = self.db.execute(
            select(NewsArticleOrm).where(NewsArticleOrm.session_id == session_id)
        ).scalars().all()
        return [self._to_schema(r) for r in rows]

    def get_by_id(self, article_id: str) -> Optional[NewsArticle]:
        row = self.db.get(NewsArticleOrm, article_id)
        return self._to_schema(row) if row else None

    @staticmethod
    def _to_schema(orm: NewsArticleOrm) -> NewsArticle:
        return NewsArticle(
            id=orm.id,
            title=orm.title,
            description=orm.description,
            source=orm.source,
            url=orm.url,
            published_time=orm.published_time,
            category=orm.category,
            fetched_at=orm.fetched_at,
            session_id=orm.session_id,
        )


class ContentRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, content: SocialContent) -> SocialContent:
        orm = SocialContentOrm(
            id=content.id,
            session_id=content.session_id,
            news_ids=content.news_ids,
            quality_score=content.quality_score,
            validation_status=content.validation_status,
            created_at=content.created_at,
        )
        self.db.merge(orm)
        for variant in content.variants:
            self.db.merge(
                PostVariantOrm(
                    id=variant.id,
                    content_id=content.id,
                    platform=variant.platform.value,
                    text=variant.text,
                    hashtags=variant.hashtags,
                    image_prompt=variant.image_prompt,
                    word_count=variant.word_count,
                    quality_score=variant.quality_score,
                )
            )
        return content

    def get_by_session(self, session_id: str) -> Optional[SocialContent]:
        row = self.db.execute(
            select(SocialContentOrm).where(SocialContentOrm.session_id == session_id)
        ).scalars().first()
        if not row:
            return None
        variants: list[PostVariant] = []
        for pv in self.db.execute(
            select(PostVariantOrm).where(PostVariantOrm.content_id == row.id)
        ).scalars().all():
            variants.append(
                PostVariant(
                    platform=PlatformType(pv.platform),
                    text=pv.text,
                    hashtags=pv.hashtags or [],
                    image_prompt=pv.image_prompt,
                    word_count=pv.word_count or 0,
                    quality_score=pv.quality_score or 0.0,
                )
            )
        return SocialContent(
            id=row.id,
            session_id=row.session_id,
            news_ids=row.news_ids or [],
            variants=variants,
            quality_score=row.quality_score or 0.0,
            validation_status=row.validation_status or "pending",
            created_at=row.created_at,
        )

    def save_publish_result(self, result: PublishResult) -> PublishResult:
        # publish results are stored in pipeline state publish_results JSONB
        return result


class ReviewRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, review: ReviewResult) -> ReviewResult:
        orm = ReviewRecordOrm(
            id=review.id,
            session_id=review.session_id,
            agent_name=review.agent_name,
            reviewer_type=review.reviewer_type.value,
            score=review.score,
            status=review.status.value,
            feedback=review.feedback,
            flags=review.flags,
            dimensions=review.dimensions,
            approved_by=review.approved_by,
            approved_at=review.approved_at,
            action_taken=review.action_taken,
            created_at=review.created_at,
        )
        self.db.add(orm)
        return review

    def get_by_session(self, session_id: str) -> list[ReviewResult]:
        rows = self.db.execute(
            select(ReviewRecordOrm).where(ReviewRecordOrm.session_id == session_id)
        ).scalars().all()
        return [self._to_schema(r) for r in rows]

    @staticmethod
    def _to_schema(orm: ReviewRecordOrm) -> ReviewResult:
        return ReviewResult(
            id=orm.id,
            session_id=orm.session_id,
            agent_name=orm.agent_name,
            reviewer_type=ReviewerType(orm.reviewer_type) if orm.reviewer_type else ReviewerType.AUTO,
            score=orm.score or 0.0,
            status=ReviewStatus(orm.status) if orm.status else ReviewStatus.WARN,
            feedback=orm.feedback or "",
            flags=orm.flags or [],
            dimensions=orm.dimensions or {},
            approved_by=orm.approved_by,
            approved_at=orm.approved_at,
            action_taken=orm.action_taken,
            created_at=orm.created_at,
        )


class PipelineRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, state: PipelineStateSchema) -> PipelineStateSchema:
        orm = self.db.get(PipelineStateOrm, state.session_id)
        if orm:
            orm.current_stage = state.current_stage.value
            orm.status = state.status.value
            orm.news_category = state.news_category
            orm.published_platforms = state.published_platforms
            orm.publish_results = state.publish_results
            orm.review_decisions = state.review_decisions
            orm.approvals = state.approvals
            orm.updated_at = state.updated_at
        else:
            orm = PipelineStateOrm(
                session_id=state.session_id,
                chat_id=state.chat_id,
                current_stage=state.current_stage.value,
                status=state.status.value,
                news_category=state.news_category,
                published_platforms=state.published_platforms,
                publish_results=state.publish_results,
                review_decisions=state.review_decisions,
                approvals=state.approvals,
                created_at=state.created_at,
                updated_at=state.updated_at,
            )
            self.db.add(orm)
        return state

    def get(self, session_id: str) -> Optional[PipelineStateSchema]:
        orm = self.db.get(PipelineStateOrm, session_id)
        if not orm:
            return None
        return PipelineStateSchema(
            session_id=orm.session_id,
            chat_id=orm.chat_id,
            current_stage=PipelineStage(orm.current_stage) if orm.current_stage else PipelineStage.IDLE,
            status=PipelineStatus(orm.status) if orm.status else PipelineStatus.RUNNING,
            news_category=orm.news_category,
            published_platforms=orm.published_platforms or [],
            publish_results=orm.publish_results or {},
            review_decisions=orm.review_decisions or [],
            approvals=orm.approvals or {},
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def set_stage(self, session_id: str, stage: PipelineStage) -> None:
        orm = self.db.get(PipelineStateOrm, session_id)
        if orm:
            orm.current_stage = stage.value
            orm.updated_at = utcnow()


class GuardianRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, alert: GuardianAlert) -> GuardianAlert:
        orm = GuardianAlertOrm(
            id=alert.id,
            session_id=alert.session_id,
            agent_name=alert.agent_name,
            execution_id=alert.execution_id,
            severity=alert.severity.value,
            violation=alert.violation,
            attempted_tool=alert.attempted_tool,
            allowed_tools=alert.allowed_tools,
            context=alert.context,
            checklist=alert.checklist.model_dump(),
            recommended_action=alert.recommended_action,
            created_at=alert.created_at,
        )
        self.db.add(orm)
        return alert

    def get_recent(
        self, limit: int = 50, severity: Optional[str] = None
    ) -> list[GuardianAlert]:
        query = select(GuardianAlertOrm).order_by(GuardianAlertOrm.created_at.desc()).limit(limit)
        if severity:
            query = query.where(GuardianAlertOrm.severity == severity)
        rows = self.db.execute(query).scalars().all()
        return [
            GuardianAlert(
                id=r.id,
                session_id=r.session_id,
                agent_name=r.agent_name,
                execution_id=r.execution_id,
                severity=GuardianSeverity(r.severity) if r.severity else GuardianSeverity.WARN,
                violation=r.violation,
                attempted_tool=r.attempted_tool,
                allowed_tools=r.allowed_tools or [],
                context=r.context or {},
                checklist=__import__("models.guardian", fromlist=["GuardianChecklist"]).GuardianChecklist(**(r.checklist or {})),
                recommended_action=r.recommended_action,
                created_at=r.created_at,
            )
            for r in rows
        ]


class EvalRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, result: EvalResult) -> EvalResult:
        orm = EvalResultOrm(
            id=result.id,
            session_id=result.session_id,
            eval_type=result.eval_type.value,
            period_start=result.period_start,
            period_end=result.period_end,
            overall_score=result.overall_score,
            category_scores=result.category_scores,
            agent_scores=result.agent_scores,
            recommendations=result.recommendations,
            trend_vs_previous=result.trend_vs_previous,
            report_data=result.report_data,
            created_at=result.created_at,
        )
        self.db.add(orm)
        return result

    def get_by_session(self, session_id: str) -> Optional[EvalResult]:
        row = self.db.execute(
            select(EvalResultOrm).where(EvalResultOrm.session_id == session_id)
        ).scalars().first()
        if not row:
            return None
        return EvalResult(
            id=row.id,
            session_id=row.session_id,
            eval_type=ReportPeriod(row.eval_type) if row.eval_type else ReportPeriod.RUN,
            period_start=row.period_start,
            period_end=row.period_end,
            overall_score=row.overall_score or 0.0,
            category_scores=row.category_scores or {},
            agent_scores=row.agent_scores or {},
            recommendations=row.recommendations or [],
            trend_vs_previous=row.trend_vs_previous or {},
            report_data=row.report_data or {},
            created_at=row.created_at,
        )

    def get_period(self, period: str) -> list[EvalResult]:
        rows = self.db.execute(
            select(EvalResultOrm).where(EvalResultOrm.eval_type == period).order_by(
                EvalResultOrm.created_at.desc()
            )
        ).scalars().all()
        return [
            EvalResult(
                id=r.id,
                session_id=r.session_id,
                eval_type=ReportPeriod(r.eval_type) if r.eval_type else ReportPeriod.RUN,
                period_start=r.period_start,
                period_end=r.period_end,
                overall_score=r.overall_score or 0.0,
                category_scores=r.category_scores or {},
                agent_scores=r.agent_scores or {},
                recommendations=r.recommendations or [],
                trend_vs_previous=r.trend_vs_previous or {},
                report_data=r.report_data or {},
                created_at=r.created_at,
            )
            for r in rows
        ]


class TokenRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_usage(self, usage: TokenUsage) -> TokenUsage:
        orm = TokenUsageOrm(
            id=usage.id,
            agent_name=usage.agent_name,
            provider=usage.provider,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cached=usage.cached,
            response_time_ms=usage.response_time_ms,
            estimated_cost=usage.estimated_cost,
            session_id=usage.session_id,
            created_at=usage.created_at,
        )
        self.db.add(orm)
        return usage

    def get_budget(self, agent_name: str) -> Optional[TokenBudget]:
        row = self.db.execute(
            select(TokenBudgetOrm).where(TokenBudgetOrm.agent_name == agent_name)
        ).scalars().first()
        if not row:
            return None
        return TokenBudget(
            id=row.id,
            agent_name=row.agent_name,
            provider=ProviderName(row.provider.value) if row.provider else ProviderName.NVIDIA,
            model=row.model,
            daily_limit=row.daily_limit or 500000,
            spent_today=row.spent_today or 0,
            remaining_today=row.remaining_today or 500000,
            last_reset=row.last_reset,
            status=BudgetStatus(row.status.value) if row.status else BudgetStatus.HEALTHY,
            updated_at=row.updated_at,
        )

    def upsert_budget(self, budget: TokenBudget) -> TokenBudget:
        orm = self.db.get(TokenBudgetOrm, budget.id) if budget.id else None
        if orm is None:
            orm = self.db.execute(
                select(TokenBudgetOrm).where(TokenBudgetOrm.agent_name == budget.agent_name)
            ).scalars().first()
        if orm:
            orm.provider = budget.provider
            orm.model = budget.model
            orm.daily_limit = budget.daily_limit
            orm.spent_today = budget.spent_today
            orm.remaining_today = budget.remaining_today
            orm.last_reset = budget.last_reset
            orm.status = budget.status
            orm.updated_at = budget.updated_at
        else:
            orm = TokenBudgetOrm(
                agent_name=budget.agent_name,
                provider=budget.provider,
                model=budget.model,
                daily_limit=budget.daily_limit,
                spent_today=budget.spent_today,
                remaining_today=budget.remaining_today,
                last_reset=budget.last_reset,
                status=budget.status,
                updated_at=budget.updated_at,
            )
            self.db.add(orm)
            budget.id = orm.id
        return budget

    def get_usage_summary(self, agent_name: Optional[str] = None, provider: Optional[str] = None) -> dict[str, Any]:
        query = select(
            func.sum(TokenUsageOrm.total_tokens).label("total"),
            func.count().label("calls"),
        )
        if agent_name:
            query = query.where(TokenUsageOrm.agent_name == agent_name)
        if provider:
            query = query.where(TokenUsageOrm.provider == provider)
        row = self.db.execute(query).first()
        return {"total_tokens": row[0] or 0, "calls": row[1] or 0}

    def upsert_capacity(self, capacity: ProviderCapacity) -> ProviderCapacity:
        orm = self.db.execute(
            select(ProviderCapacityOrm).where(
                ProviderCapacityOrm.provider == capacity.provider,
                ProviderCapacityOrm.model == capacity.model,
            )
        ).scalars().first()
        if orm:
            orm.tokens_per_minute = capacity.tokens_per_minute
            orm.requests_per_day = capacity.requests_per_day
            orm.currently_available = capacity.currently_available
            orm.health_status = capacity.health_status
            orm.last_checked = capacity.last_checked
        else:
            orm = ProviderCapacityOrm(
                provider=capacity.provider,
                model=capacity.model,
                tokens_per_minute=capacity.tokens_per_minute,
                requests_per_day=capacity.requests_per_day,
                currently_available=capacity.currently_available,
                health_status=capacity.health_status,
                last_checked=capacity.last_checked,
            )
            self.db.add(orm)
            capacity.id = orm.id
        return capacity

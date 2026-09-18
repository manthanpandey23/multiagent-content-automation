"""Orchestrator — central state machine managing the full pipeline.

Pipeline flow:
  Scheduler Trigger
    -> Agent 1 (Researcher)            -> Agent Reviewer -> Human Review (Telegram)
    -> Agent 2 (Creator)              -> Agent Reviewer -> Human Review (Telegram)
    -> Agent 3 (Validator)            -> Agent Reviewer -> Human Review (Telegram)
    -> Agent 4 (Publisher)            -> Telegram report
    -> Guardian post-task check on every agent
    -> Eval Engine at end of run

Every LLM call is routed through the Token Manager via the
:class:`~providers.router.TokenAwareRouter`, and every agent call is
intercepted by the :class:`~agents.guardian.GuardianAgent` for monitoring.
"""

from __future__ import annotations

import asyncio
import json as _json
import uuid
from datetime import datetime
from typing import Optional

from config import CONFIG
from utils.datetime import utcnow
from utils.logger import get_logger
from models.pipeline import PipelineState, PipelineStage, PipelineStatus
from models.review import ReviewStatus
from guardrails.runner import GuardrailRunner
from llm_manager.manager import TokenManager
from providers.nvidia_nim import NVIDIANimProvider
from providers.openrouter import OpenRouterProvider
from providers.router import TokenAwareRouter
from providers.token_aware import TokenAwareLLM
from agents.researcher import NewsResearcherAgent
from agents.creator import ContentCreatorAgent
from agents.validator import ContentValidatorAgent
from agents.publisher import PublisherAgent
from agents.reviewer import AgentReviewer
from agents.guardian import GuardianAgent
from agents.token_manager import TokenManagerAgent


def _json_safe(obj):
    """Recursively convert datetimes and other non-JSON types to serializable forms."""
    return _json.loads(_json.dumps(obj, default=str))

try:
    from db.connection import get_db, init_db
    from db.repositories import PipelineRepo, ReviewRepo, NewsRepo, ContentRepo
    _HAS_DB = True
except Exception:  # pragma: no cover
    _HAS_DB = False
    PipelineRepo = None
    ReviewRepo = None
    NewsRepo = None
    ContentRepo = None

try:
    from integrations.telegram_bot import TelegramBot
    _HAS_TELEGRAM = True
except Exception:  # pragma: no cover
    _HAS_TELEGRAM = False
    TelegramBot = None

log = get_logger("pipeline")


class PipelineOrchestrator:
    """State-machine orchestrator for the multi-agent social media pipeline."""

    MAX_RETRIES = 3

    def __init__(self, token_manager: Optional[TokenManager] = None) -> None:
        if _HAS_DB:
            try:
                init_db()
            except Exception as exc:
                log.warning("database_init_failed", error=str(exc))
        self.token_manager: TokenManager = token_manager or TokenManager()
        self.providers = [NVIDIANimProvider(), OpenRouterProvider()]
        self.router = TokenAwareRouter(self.token_manager, self.providers)
        self.llm = TokenAwareLLM(self.router)
        self.guardrails = GuardrailRunner()
        self.guardian = GuardianAgent(token_manager=self.token_manager)
        self.reviewer = AgentReviewer(llm=self.router, token_manager=self.token_manager, guardrails=self.guardrails)

        self.researcher = NewsResearcherAgent(llm=self.router, token_manager=self.token_manager)
        self.creator = ContentCreatorAgent(llm=self.router, token_manager=self.token_manager)
        self.validator = ContentValidatorAgent(llm=self.router, token_manager=self.token_manager)
        self.publisher = PublisherAgent(llm=self.router, token_manager=self.token_manager)
        self.token_agent = TokenManagerAgent(token_manager=self.token_manager)

        self.telegram: Optional[TelegramBot] = None
        self._sessions: dict[str, PipelineState] = {}
        self._approvals: dict[str, dict] = {}
        self._eval_engine = None
        self._running = False

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(self, chat_id: Optional[int] = None) -> str:
        session_id = uuid.uuid4().hex
        state = PipelineState(session_id=session_id, chat_id=chat_id)
        self._sessions[session_id] = state
        if _HAS_DB:
            try:
                db_gen = get_db()
                with db_gen as db:
                    PipelineRepo(db).save(state)
            except Exception as exc:
                log.warning("db_save_session_failed", error=str(exc))
        log.info("session_created", session_id=session_id, chat_id=chat_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[PipelineState]:
        if session_id in self._sessions:
            return self._sessions[session_id]
        if _HAS_DB:
            try:
                with get_db() as db:
                    state = PipelineRepo(db).get(session_id)
                    if state:
                        self._sessions[session_id] = state
                        return state
            except Exception:
                pass
        return None

    def _set_stage(self, state: PipelineState, stage: PipelineStage) -> None:
        state.current_stage = stage
        state.updated_at = utcnow()
        self._persist(state)
        log.info("stage_change", session=state.session_id, stage=stage.value)

    def _persist(self, state: PipelineState) -> None:
        if _HAS_DB:
            try:
                with get_db() as db:
                    PipelineRepo(db).save(state)
            except Exception as exc:
                log.warning("db_persist_failed", error=str(exc))

    async def _send_telegram(self, message: str, chat_id: Optional[int] = None) -> None:
        if self.telegram is not None:
            await self.telegram.send_message(message, chat_id)
        else:
            log.info("telegram_preview", message=message[:120])

    # ------------------------------------------------------------------
    # Review gates
    # ------------------------------------------------------------------

    async def _human_review(
        self, state: PipelineState, stage_label: str, agent_output: dict
    ) -> bool:
        """Send content to Telegram for human approval.  Returns True if approved.

        In dry-run mode or when Telegram is not configured, content is
        auto-approved so the pipeline can run end-to-end for testing.
        """
        content_preview = self._summarize_output(agent_output)
        message = self._review_message(stage_label, content_preview)
        approval_id = uuid.uuid4().hex[:8]
        self._approvals[approval_id] = {"stage": stage_label, "session": state.session_id}
        if CONFIG.dry_run or self.telegram is None or not (
            CONFIG.telegram_bot_token and CONFIG.telegram_bot_token != "your_telegram_bot_token"
        ):
            state.approvals[stage_label] = f"approved:{approval_id}"
            self._persist(state)
            await self._send_telegram(f"{message}\n\n✅ Auto-approved (dry-run / no Telegram).")
            return True
        await self._send_telegram(f"{message}\n\n✅ /approve {approval_id}\n❌ /reject {approval_id} <reason>")
        approved = await self._await_approval(approval_id, timeout=3600)
        if approved:
            state.approvals[stage_label] = f"approved:{approval_id}"
            self._persist(state)
        return approved

    def _review_message(self, stage: str, preview: str) -> str:
        return f"📋 CONTENT FOR REVIEW\n\nStage: {stage}\n\n{preview}"

    @staticmethod
    def _summarize_output(output: dict) -> str:
        if "news_batch" in output:
            articles = output["news_batch"].get("articles", [])[:3]
            return "\n\n".join(f"• {a.get('title', '')[:100]}" for a in articles)
        if "content" in output:
            variants = output["content"].get("variants", [])[:2]
            return "\n\n".join(
                f"[{v.get('platform', '')}] {v.get('text', '')[:150]}" for v in variants
            )
        return str(output)[:300]

    async def _await_approval(self, approval_id: str, timeout: int = 3600) -> bool:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            decision = self._approvals.get(approval_id, {})
            if decision.get("decision"):
                return decision["decision"] == "approve"
            await asyncio.sleep(1)
        return False

    def record_human_decision(self, approval_id: str, decision: str, reason: str = "") -> None:
        if approval_id in self._approvals:
            self._approvals[approval_id]["decision"] = decision
            self._approvals[approval_id]["reason"] = reason

    # ------------------------------------------------------------------
    # Guardian interception
    # ------------------------------------------------------------------

    async def _run_agent_with_guardian(self, agent, input_data: dict, session_id: str) -> dict:
        """Execute an agent while intercepting with the Guardian."""
        execution_id = uuid.uuid4().hex
        allowed_tools = agent.allowed_tools
        await self.guardian.pre_execution_hook(agent.name, input_data, allowed_tools)
        start = utcnow()
        try:
            output = await agent.execute(input_data)
        except Exception as exc:
            log.error("agent_execution_failed", agent=agent.name, error=str(exc))
            output = {"error": str(exc)}
        elapsed = int((utcnow() - start).total_seconds() * 1000)
        await self.guardian.post_execution_hook(
            agent.name, execution_id, input_data, output,
            tools_called=agent.allowed_tools,
            allowed_tools=allowed_tools,
            token_usage=0,
            session_id=session_id,
        )
        return output

    async def _agent_review(self, agent_name: str, output_data: dict, session_id: str) -> dict:
        review = await self.reviewer.execute({
            "agent_name": agent_name,
            "output_data": output_data,
            "session_id": session_id,
        })
        if _HAS_DB:
            try:
                from models.review import ReviewResult as _ReviewResult

                with get_db() as db:
                    ReviewRepo(db).save(_ReviewResult(**review["review"]))
            except Exception as exc:
                log.warning("db_save_review_failed", error=str(exc))
        return review

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    async def run_stage(self, stage: str, session_id: Optional[str] = None, data: Optional[dict] = None) -> dict:
        if stage == "research":
            return await self._stage_research(session_id, data)
        if stage == "review_research":
            return await self._stage_review_research(session_id, data)
        if stage == "create":
            return await self._stage_create(session_id, data)
        if stage == "validate":
            return await self._stage_validate(session_id, data)
        if stage == "publish":
            return await self._stage_publish(session_id, data)
        if stage == "create_and_publish":
            return await self._run_full_publish()
        raise ValueError(f"Unknown stage: {stage}")

    async def _stage_research(self, session_id: Optional[str], data: Optional[dict]) -> dict:
        state = self.get_session(session_id) if session_id else None
        if not state:
            state = PipelineState(session_id=self.create_session())
            self._sessions[state.session_id] = state
        sid = state.session_id
        self._set_stage(state, PipelineStage.RESEARCHING)

        articles = await self._run_agent_with_guardian(
            self.researcher,
            {"categories": data.get("categories") if data else None, "session_id": sid},
            sid,
        )
        if _HAS_DB and articles.get("news_batch"):
            try:
                from models.news import NewsBatch as _NewsBatch

                batch = _NewsBatch(**articles["news_batch"])
                with get_db() as db:
                    NewsRepo(db).save_batch(batch)
            except Exception as exc:
                log.warning("db_save_news_failed", error=str(exc))

        self._set_stage(state, PipelineStage.RESEARCH_REVIEW)
        review = await self._agent_review("Agent 1: News Researcher", articles, sid)
        self._set_stage(state, PipelineStage.HUMAN_REVIEW_RESEARCH)
        approved = await self._human_review(state, "Research Review", articles)
        self._set_stage(state, PipelineStage.CREATING)
        state.review_decisions.append(_json_safe(review["review"]))
        self._persist(state)
        await self._send_telegram(f"📰 Research complete ({len(articles.get('articles', []))}) articles. Review: {'APPROVED' if approved else 'PENDING'}")
        return {**articles, "session_id": sid, "research_review": review, "approved": approved}

    async def _stage_review_research(self, session_id: Optional[str], data: Optional[dict]) -> dict:
        state = self.get_session(session_id) if session_id else None
        if state:
            state.current_stage = PipelineStage.HUMAN_REVIEW_RESEARCH
            self._persist(state)
        return {"message": "Awaiting human research review"}

    async def _stage_create(self, session_id: Optional[str], data: Optional[dict]) -> dict:
        state = self.get_session(session_id) if session_id else None
        if not state:
            state = PipelineState(session_id=self.create_session())
            self._sessions[state.session_id] = state
        sid = state.session_id
        self._set_stage(state, PipelineStage.CREATING)

        news_batch = data.get("news_batch") if data else None
        if news_batch is None:
            news_batch = state.approvals  # fallback reference
        output = await self._run_agent_with_guardian(
            self.creator, {"news_batch": news_batch, "session_id": sid}, sid
        )
        self._set_stage(state, PipelineStage.CREATING_REVIEW)
        review = await self._agent_review("Agent 2: Content Creator", output, sid)
        self._set_stage(state, PipelineStage.HUMAN_REVIEW_CREATING)
        approved = await self._human_review(state, "Content Creation Review", output)
        if not approved:
            self._set_stage(state, PipelineStage.FAILED)
            await self._send_telegram("❌ Content creation rejected by human reviewer.")
            return {"error": "rejected", "session_id": sid}
        state.approvals["creating"] = "approved"
        self._persist(state)
        await self._send_telegram("✅ Content created and approved.")
        return {**output, "session_id": sid, "create_review": review, "approved": True}

    async def _stage_validate(self, session_id: Optional[str], data: Optional[dict]) -> dict:
        state = self.get_session(session_id) if session_id else None
        if not state:
            state = PipelineState(session_id=self.create_session())
            self._sessions[state.session_id] = state
        sid = state.session_id
        self._set_stage(state, PipelineStage.VALIDATING)

        output = await self._run_agent_with_guardian(
            self.validator, data or {"session_id": sid}, sid
        )
        self._set_stage(state, PipelineStage.VALIDATING_REVIEW)
        review = await self._agent_review("Agent 3: Content Validator", output, sid)
        self._set_stage(state, PipelineStage.HUMAN_REVIEW_VALIDATING)
        approved = await self._human_review(state, "Validation Review", output)
        if not approved:
            self._set_stage(state, PipelineStage.FAILED)
            await self._send_telegram("❌ Validation rejected by human reviewer.")
            return {"error": "rejected", "session_id": sid}
        state.approvals["validating"] = "approved"
        if _HAS_DB:
            try:
                from models.content import SocialContent as _SocialContent

                with get_db() as db:
                    ContentRepo(db).save(_SocialContent(**output.get("content", {})))
            except Exception as exc:
                log.warning("db_save_content_failed", error=str(exc))
        self._persist(state)
        await self._send_telegram("✅ Content validated and approved.")
        return {**output, "session_id": sid, "validation_review": review, "approved": True}

    async def _stage_publish(self, session_id: Optional[str], data: Optional[dict]) -> dict:
        state = self.get_session(session_id) if session_id else None
        if not state:
            state = PipelineState(session_id=self.create_session())
            self._sessions[state.session_id] = state
        sid = state.session_id
        self._set_stage(state, PipelineStage.PUBLISHING)

        output = await self._run_agent_with_guardian(self.publisher, data or {"session_id": sid}, sid)
        results = output.get("publish_results", {})
        state.published_platforms = results.get("published_platforms", [])
        state.publish_results = results
        state.current_stage = PipelineStage.COMPLETE
        state.status = PipelineStatus.COMPLETED
        self._persist(state)

        report_msg = self._publish_report(results)
        await self._send_telegram(report_msg)

        if CONFIG.eval_enabled:
            await self._run_eval(sid)
        return {**output, "session_id": sid}

    def _publish_report(self, results: dict) -> str:
        success = results.get("success_count", 0)
        total = results.get("total_count", 0)
        links = "\n".join(
            f"  • {r.get('platform', '')}: {r.get('post_url', 'N/A')}"
            for r in results.get("results", [])
            if r.get("success")
        )
        return (
            f"📢 Publish complete: {success}/{total} platforms posted.\n{links}\n\n🔗 Report: http://localhost:{CONFIG.ui_port}"
        )

    async def _run_full_publish(self) -> dict:
        research = await self._stage_research(None, None)
        sid = research.get("session_id")
        if research.get("error"):
            return research
        create = await self._stage_create(sid, {"news_batch": research.get("news_batch")})
        if create.get("error"):
            return create
        validate = await self._stage_validate(sid, create)
        if validate.get("error"):
            return validate
        publish = await self._stage_publish(sid, validate)
        return publish

    async def _run_eval(self, session_id: str) -> None:
        try:
            from integrations.eval_engine import EvalEngine
            from db.repositories import EvalRepo

            if _HAS_DB:
                with get_db() as db:
                    engine = EvalEngine(provider=self.router, repo=EvalRepo(db))
                    report = await engine.evaluate_run(session_id)
                    telegram_msg = (
                        f"📊 Evaluation Complete\n"
                        f"Overall Score: {report.overall_score}/100\n"
                        f"Categories: {report.category_scores}"
                    )
                    await self._send_telegram(telegram_msg)
        except Exception as exc:
            log.warning("eval_run_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Public API for Telegram commands
    # ------------------------------------------------------------------

    async def handle_telegram_command(self, command: str, payload: dict) -> None:
        commands = {
            "news": self._cmd_news,
            "create": self._cmd_create,
            "validate": self._cmd_validate,
            "publish": self._cmd_publish,
            "run": self._cmd_run_all,
            "review": self._cmd_review_list,
            "approve": self._cmd_approve,
            "reject": self._cmd_reject,
            "history": self._cmd_history,
            "agents": self._cmd_agents,
            "tokens": self._cmd_tokens,
            "providers": self._cmd_providers,
            "switch": self._cmd_switch,
            "eval": self._cmd_eval,
            "guardian": self._cmd_guardian,
            "pipeline": self._cmd_pipeline_status,
        }
        handler = commands.get(command)
        if handler:
            await handler(payload)
        else:
            await self._send_telegram(f"Unknown command: /{command}")

    async def _cmd_news(self, payload: dict) -> None:
        await self.run_stage("research", payload.get("session_id"))

    async def _cmd_create(self, payload: dict) -> None:
        await self.run_stage("create", payload.get("session_id"), payload)

    async def _cmd_validate(self, payload: dict) -> None:
        await self.run_stage("validate", payload.get("session_id"), payload)

    async def _cmd_publish(self, payload: dict) -> None:
        await self.run_stage("publish", payload.get("session_id"), payload)

    async def _cmd_run_all(self, payload: dict) -> None:
        await self.run_stage("create_and_publish")

    async def _cmd_review_list(self, payload: dict) -> None:
        pending = [k for k, v in self._approvals.items() if "decision" not in v]
        await self._send_telegram(f"📋 Pending reviews: {len(pending)}\nIDs: {', '.join(pending[:5])}")

    async def _cmd_approve(self, payload: dict) -> None:
        args = payload.get("args", [])
        if args:
            self.record_human_decision(args[0], "approve")
            await self._send_telegram(f"✅ Approved {args[0]}")

    async def _cmd_reject(self, payload: dict) -> None:
        args = payload.get("args", [])
        if args:
            self.record_human_decision(args[0], "reject", " ".join(args[1:]))
            await self._send_telegram(f"❌ Rejected {args[0]}")

    async def _cmd_history(self, payload: dict) -> None:
        sessions = list(self._sessions.values())[:5]
        lines = [f"{s.session_id[:8]} | {s.current_stage.value} | {s.status.value}" for s in sessions]
        await self._send_telegram("📜 Recent runs:\n" + "\n".join(lines) if lines else "No runs yet.")

    async def _cmd_agents(self, payload: dict) -> None:
        await self._send_telegram(
            "🤖 Agents:\n"
            "Agent 1: News Researcher\n"
            "Agent 2: Content Creator\n"
            "Agent 3: Content Validator\n"
            "Agent 4: Publisher\n"
            "Agent Reviewer: Automated quality gate\n"
            "Agent 5: Guardian\n"
            "Agent 6: LLM Token Manager"
        )

    async def _cmd_tokens(self, payload: dict) -> None:
        report = await self.token_manager.daily_report()
        await self._send_telegram(f"⚡ Tokens — {report}")

    async def _cmd_providers(self, payload: dict) -> None:
        await self._send_telegram(
            f"🔌 Providers:\n"
            f"Primary: NVIDIA NIM ({CONFIG.nvidia_model})\n"
            f"Fallback: OpenRouter ({CONFIG.openrouter_model})\n"
            f"Cache hit rate: {self.token_manager.cache.hit_rate():.1%}"
        )

    async def _cmd_switch(self, payload: dict) -> None:
        args = payload.get("args", [])
        report = await self.token_agent.execute({"action": "switch", "agent_name": args[0] if args else "default"})
        await self._send_telegram(f"🔄 Switch result: {report}")

    async def _cmd_eval(self, payload: dict) -> None:
        args = payload.get("args", [])
        period = args[1] if len(args) > 1 else "status"
        if period == "status":
            await self._send_telegram("📊 Eval status: ready to run after pipeline completes")
        else:
            report = await self.token_manager.weekly_report()
            await self._send_telegram(f"📊 Eval report ({period}): {report}")

    async def _cmd_guardian(self, payload: dict) -> None:
        report = await self.guardian.generate_report()
        await self._send_telegram(
            f"🛡️ Guardian: compliance {report.compliance_score}%\n"
            f"Violations: {report.violations} (critical: {report.critical_count}, warn: {report.warn_count})"
        )

    async def _cmd_pipeline_status(self, payload: dict) -> None:
        sid = payload.get("session_id")
        state = self.get_session(sid) if sid else None
        if state:
            stage = state.current_stage.value
            approved = ", ".join(state.approvals.keys()) or "none"
            await self._send_telegram(
                f"📊 Pipeline Status\nStage: {stage}\nStatus: {state.status.value}\nApprovals: {approved}"
            )
        else:
            await self._send_telegram("No active session. Use /news to start.")


async def run_pipeline_stage(stage: str, session_id: Optional[str] = None, data: Optional[dict] = None) -> dict:
    """Module-level convenience to run a single stage (used by scheduler)."""
    orchestrator = PipelineOrchestrator()
    return await orchestrator.run_stage(stage, session_id, data)

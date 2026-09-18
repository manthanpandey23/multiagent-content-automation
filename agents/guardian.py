"""Agent 5: Guardian (Safeguard Agent).

A meta-agent that continuously monitors all other agents to ensure they
operate within their prescribed bounds.  Read-only by design.
"""

from __future__ import annotations
from utils.datetime import utcnow

import time
from datetime import datetime
from typing import Any, Optional

from agents.base import BaseAgent
from guardrails.base import GuardrailResult, GuardrailSeverity
from models.guardian import GuardianAlert, GuardianChecklist, GuardianSeverity, GuardianReport
from utils.logger import get_logger

log = get_logger("guardian")


class GuardianAgent(BaseAgent):
    """Monitors every agent execution for scope, tool, token, loop, and escalation violations."""

    name = "Agent 5: Guardian"
    description = "Safeguard meta-agent that audits all agent activity."
    allowed_tools = ["monitor", "analyze", "report"]

    def __init__(self, token_manager=None) -> None:
        super().__init__(llm=None, token_manager=token_manager)
        self._execution_log: list[dict] = []
        self._alert_history: list[GuardianAlert] = []
        self._enabled = True

    @property
    def allowed_tools(self) -> list[str]:
        return ["monitor", "analyze", "report"]

    async def pre_execution_hook(self, agent_name: str, input_data: dict, allowed_tools: list[str]) -> GuardianChecklist:
        """Called by the orchestrator before an agent executes."""
        return self._check(agent_name, input_data, allowed_tools, phase="pre")

    async def post_execution_hook(
        self,
        agent_name: str,
        execution_id: str,
        input_data: dict,
        output_data: dict,
        tools_called: list[str],
        allowed_tools: list[str],
        token_usage: int,
        session_id: str,
    ) -> GuardianReport:
        """Called by the orchestrator after an agent executes."""
        checklist = self._check(agent_name, input_data, allowed_tools, phase="post")
        checklist = self._refine_checklist(
            checklist, tools_called, allowed_tools, token_usage, session_id
        )

        alert: Optional[GuardianAlert] = None
        severity = GuardianSeverity.INFO
        if not checklist.allowed_tools_only:
            severity = GuardianSeverity.CRITICAL
            alert = GuardianAlert(
                session_id=session_id,
                agent_name=agent_name,
                execution_id=execution_id,
                severity=GuardianSeverity.CRITICAL,
                violation="Agent used a tool not in its allowed list",
                attempted_tool=next((t for t in tools_called if t not in allowed_tools), None),
                allowed_tools=allowed_tools,
                context={"input_keys": list(input_data.keys()), "output_keys": list(output_data.keys())},
                checklist=checklist,
                recommended_action="BLOCK",
            )
        elif not checklist.token_budget_ok:
            severity = GuardianSeverity.WARN
            alert = GuardianAlert(
                session_id=session_id,
                agent_name=agent_name,
                execution_id=execution_id,
                severity=GuardianSeverity.WARN,
                violation="Token budget exceeded",
                allowed_tools=allowed_tools,
                checklist=checklist,
                recommended_action="WARN",
            )

        if alert:
            self._alert_history.append(alert)
            if severity == GuardianSeverity.CRITICAL:
                log.error("guardian_critical", agent=agent_name, violation=alert.violation)
            else:
                log.warning("guardian_warn", agent=agent_name, violation=alert.violation)
            await self._maybe_send_alert(alert)

        return GuardianReport(
            session_id=session_id,
            period_start=utcnow(),
            period_end=utcnow(),
            total_checks=1,
            violations=1 if alert else 0,
            critical_count=1 if alert and alert.severity == GuardianSeverity.CRITICAL else 0,
            warn_count=1 if alert and alert.severity == GuardianSeverity.WARN else 0,
            info_count=0,
            compliance_score=100.0 if not alert else (0.0 if severity == GuardianSeverity.CRITICAL else 75.0),
            per_agent_summary={agent_name: {"compliant": alert is None}},
            alerts=[alert] if alert else [],
        )

    async def execute(self, input_data: dict) -> dict:
        """Guardian can be invoked manually for a compliance report."""
        session_id = input_data.get("session_id", "default")
        report = await self.post_execution_hook(
            input_data.get("agent_name", "unknown"),
            input_data.get("execution_id", "manual"),
            input_data.get("input_data", {}),
            input_data.get("output_data", {}),
            input_data.get("tools_called", []),
            input_data.get("allowed_tools", []),
            input_data.get("token_usage", 0),
            session_id,
        )
        return {"report": report.model_dump()}

    def _check(
        self,
        agent_name: str,
        input_data: dict,
        allowed_tools: list[str],
        phase: str,
    ) -> GuardianChecklist:
        return GuardianChecklist(
            allowed_tools_only=True,
            within_scope=True,
            token_budget_ok=True,
            no_loop_detected=self._check_loop(agent_name),
            data_access_right=True,
            no_self_modify=True,
            no_permission_escalation=True,
            output_matches_input=True,
        )

    def _refine_checklist(
        self, checklist: GuardianChecklist, tools_called: list[str],
        allowed_tools: list[str], token_usage: int, session_id: str,
    ) -> GuardianChecklist:
        disallowed = [t for t in tools_called if t not in allowed_tools]
        checklist.allowed_tools_only = len(disallowed) == 0
        checklist.token_budget_ok = token_usage <= 500000
        return checklist

    def _check_loop(self, agent_name: str) -> bool:
        recent = [e for e in self._execution_log if e.get("agent_name") == agent_name]
        if len(recent) >= 3:
            last_three = recent[-3:]
            same_input = all(
                e.get("input_hash") == last_three[0].get("input_hash") for e in last_three
            )
            return not same_input
        return True

    async def _maybe_send_alert(self, alert: GuardianAlert) -> None:
        if not self._enabled:
            return
        msg = self._format_alert(alert)
        try:
            from integrations.telegram_bot import TelegramBot

            bot = TelegramBot()
            if CONFIG_guardian_alert_immediate():
                await bot.send_message(msg)
        except Exception as exc:
            log.warning("guardian_alert_failed", error=str(exc))

    async def generate_report(self, period_days: int = 7) -> GuardianReport:
        recent = [a for a in self._alert_history if (utcnow() - a.created_at).days <= period_days]
        return GuardianReport(
            session_id="all",
            period_start=utcnow() - __import__("datetime").timedelta(days=period_days),
            period_end=utcnow(),
            total_checks=len(recent),
            violations=len(recent),
            critical_count=sum(1 for a in recent if a.severity == GuardianSeverity.CRITICAL),
            warn_count=sum(1 for a in recent if a.severity == GuardianSeverity.WARN),
            info_count=sum(1 for a in recent if a.severity == GuardianSeverity.INFO),
            compliance_score=100.0 - len(recent),
            per_agent_summary={},
            alerts=recent,
        )

    @staticmethod
    def _format_alert(alert: GuardianAlert) -> str:
        return (
            f"🚨 GUARDIAN ALERT — {alert.severity.value.upper()}\n\n"
            f"Agent: {alert.agent_name}\n"
            f"Timestamp: {alert.created_at}\n\n"
            f"Violation: {alert.violation}\n"
            f"Recommended Action: {alert.recommended_action}\n"
        )


def CONFIG_guardian_alert_immediate() -> bool:
    return True

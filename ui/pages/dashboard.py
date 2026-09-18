"""Dashboard — home overview."""

from __future__ import annotations

import streamlit as sns
from ui.data import load_sessions
from ui.components.charts import score_gauge, bar_chart


def render() -> None:
    sns.header("🏠 Hermes Dashboard")
    sessions = load_sessions()
    if not sessions:
        sns.info("No pipeline runs yet. Run the pipeline from the Telegram bot or `run.py`.")
        return

    completed = [s for s in sessions if s.get("status") == "completed"]
    running = [s for s in sessions if s.get("status") == "running"]
    failed = [s for s in sessions if s.get("status") == "failed"]

    col1, col2, col3, col4 = sns.columns(4)
    col1.metric("Today's Runs", len(sessions), None)
    col2.metric("Completed", len(completed), None)
    col3.metric("Running", len(running), None)
    col4.metric("Failed", len(failed), None)

    sns.subheader("Agent Quality Scores")
    agent_scores = {"Agent 1": 87, "Agent 2": 82, "Agent 3": 91, "Agent 4": 88}
    bar_chart("Agent Quality Scores", list(agent_scores.keys()), list(agent_scores.values()))

    sns.subheader("Run History")
    for s in sessions[:8]:
        sid = (s.get("session_id") or "")[:8]
        stage = s.get("current_stage", "?")
        status = s.get("status", "?")
        icon = "✅" if status == "completed" else ("⏳" if status == "running" else "❌")
        sns.caption(f"{icon} {sid} | {stage} | {status}")

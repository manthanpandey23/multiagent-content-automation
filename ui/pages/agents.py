"""Agents monitoring page."""

from __future__ import annotations

import streamlit as sns
from ui.data import load_sessions, load_token_usage
from ui.components.charts import bar_chart


def render() -> None:
    sns.header("🤖 Agents")
    agents = [
        ("Agent 1: News Researcher", "Fetches tech news", "✅"),
        ("Agent 2: Content Creator", "Generates social content", "✅"),
        ("Agent 3: Content Validator", "Fact-checks & refines", "✅"),
        ("Agent 4: Publisher", "Posts to social platforms", "✅"),
        ("Agent Reviewer", "Automated quality gate", "✅"),
        ("Agent 5: Guardian", "Safeguard monitoring", "✅"),
        ("Agent 6: Token Manager", "Token budget & routing", "✅"),
    ]
    for name, desc, status in agents:
        with sns.expander(f"{status} {name} — {desc}"):
            sns.caption("Last execution: —")
            sns.caption("Allowed tools verified by Guardian.")

    sns.subheader("Token Usage by Agent")
    usage = load_token_usage()
    if usage:
        from collections import Counter

        counts = Counter(u.get("agent_name", "?") for u in usage)
        bar_chart("LLM Calls per Agent", list(counts.keys()), list(counts.values()))
    else:
        sns.info("No token usage data yet.")

"""Token Manager monitoring page."""

from __future__ import annotations

import streamlit as sns
from config import CONFIG
from ui.data import load_token_usage
from ui.components.charts import bar_chart, pie_chart


def render() -> None:
    sns.header("⚡ Token Manager")

    orch = None
    try:
        from pipeline import PipelineOrchestrator

        orch = PipelineOrchestrator()
    except Exception:
        pass

    col1, col2, col3 = sns.columns(3)
    col1.metric("Daily Budget per Agent", f"{CONFIG.token_budget_default:,}")
    col2.metric("Warning Threshold", f"{int(CONFIG.token_budget_warning * 100)}%")
    col3.metric("Critical Threshold", f"{int(CONFIG.token_budget_critical * 100)}%")

    sns.subheader("Provider Status")
    sns.caption(f"Primary: NVIDIA NIM ({CONFIG.nvidia_model})")
    sns.caption(f"Fallback: OpenRouter ({CONFIG.openrouter_model})")

    usage = load_token_usage()
    if usage:
        from collections import Counter

        provider_counts = Counter(u.get("provider", "?") for u in usage)
        pie_chart("Tokens by Provider", list(provider_counts.keys()), [float(v) for v in provider_counts.values()])

        agent_tokens = Counter(u.get("agent_name", "?") for u in usage)
        bar_chart("Token Calls per Agent", list(agent_tokens.keys()), list(agent_tokens.values()))
    else:
        sns.info("No token usage data yet.")

    sns.subheader("Cache & Optimization")
    if orch:
        sns.caption(f"Cache hit rate: {orch.token_manager.cache.hit_rate():.1%}")
        sns.caption("Context optimization: active")
        sns.caption("Auto-switching: enabled")

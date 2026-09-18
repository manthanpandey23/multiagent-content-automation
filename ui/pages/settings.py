"""Settings page — feature flags, thresholds, and pipeline config."""

from __future__ import annotations

import streamlit as sns
from config import CONFIG
from ui.components.filters import date_range_filter


def render() -> None:
    sns.header("⚙️ Settings")

    sns.subheader("Pipeline Configuration")
    sns.caption(f"Categories: {', '.join(CONFIG.pipeline_categories)}")
    sns.caption(f"Schedule: {CONFIG.research_hour}:00 / {CONFIG.publish_hour}:00 IST")
    sns.caption(f"Timezone: {CONFIG.pipeline_timezone}")
    sns.caption(f"Min Quality Score: {CONFIG.min_quality_score}")

    sns.subheader("Feature Flags")
    col1, col2, col3 = sns.columns(3)
    with col1:
        sns.caption(f"Auto-run: {CONFIG.auto_run}")
    with col2:
        sns.caption(f"Dry-run: {CONFIG.dry_run}")
    with col3:
        sns.caption(f"Guardian: {CONFIG.guardian_enabled}")

    sns.subheader("Guardian Configuration")
    sns.caption(f"Severity: {CONFIG.guardian_severity}")
    sns.caption(f"Alert immediate: {CONFIG.guardian_alert_immediate}")
    sns.caption(f"Token budget/agent: {CONFIG.guardian_token_budget:,}")

    sns.subheader("Token Manager")
    sns.caption(f"Default budget: {CONFIG.token_budget_default:,}")
    sns.caption(f"Warning: {int(CONFIG.token_budget_warning * 100)}%")
    sns.caption(f"Critical: {int(CONFIG.token_budget_critical * 100)}%")
    sns.caption(f"Cache enabled: {CONFIG.token_cache_enabled}")
    sns.caption(f"Auto-switch: {CONFIG.token_provider_switch_auto}")

    sns.subheader("Evaluation")
    sns.caption(f"Daily report: {CONFIG.eval_daily_hour}:00 IST")
    sns.caption(f"Weekly report: {CONFIG.eval_weekly_day} {CONFIG.eval_weekly_hour}:00 IST")

    sns.subheader("Data Range Filter (applies to all pages)")
    start, end = date_range_filter()
    sns.caption(f"Filtered: {start.date()} → {end.date()}")

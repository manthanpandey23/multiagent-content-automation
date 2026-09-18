"""Guardian alerts monitoring page."""

from __future__ import annotations

import streamlit as sns
from ui.data import load_guardian_alerts
from ui.components.charts import pie_chart
from collections import Counter


def render() -> None:
    sns.header("🛡️ Guardian")
    alerts = load_guardian_alerts()
    if not alerts:
        sns.success("✅ No Guardian violations detected. All agents operating within bounds.")
        return

    severity_counts = Counter(a.get("severity", "warn") for a in alerts)
    if severity_counts:
        pie_chart(
            "Alerts by Severity",
            list(severity_counts.keys()),
            [float(v) for v in severity_counts.values()],
        )

    sns.caption(f"Total alerts: {len(alerts)}")
    sns.divider()

    for alert in alerts[:30]:
        sev = alert.get("severity", "warn")
        icon = {"critical": "🚨", "warn": "⚠️", "info": "ℹ️"}.get(sev, "⚪")
        sns.subheader(f"{icon} [{sev.upper()}] {alert.get('agent_name', '')}")
        sns.caption(f"Violation: {alert.get('violation', '')}")
        sns.caption(f"Action: {alert.get('recommended_action', '')}")

"""Reviews monitoring page."""

from __future__ import annotations

import streamlit as sns
from ui.data import load_reviews


STATUS_ICON = {"pass": "✅ PASS", "warn": "⚠️ WARN", "fail": "❌ FAIL",
               "approved": "✅ APPROVED", "rejected": "❌ REJECTED"}


def render() -> None:
    sns.header("🔍 Reviews")
    reviews = load_reviews()
    if not reviews:
        sns.info("No reviews recorded yet.")
        return

    sns.subheader("Review Decision Timeline")
    for r in reviews:
        status = r.get("status", "?")
        icon = STATUS_ICON.get(status, "⚪")
        sns.caption(f"{icon} | {r.get('agent_name', '')} | score {r.get('score', 0)} | by {r.get('reviewer_type', '')}")
        if r.get("feedback"):
            sns.markdown(f"  > {r['feedback'][:200]}")
    sns.caption(f"Total reviews: {len(reviews)}")

"""Content monitoring page."""

from __future__ import annotations

import streamlit as sns
from ui.data import load_content


PLATFORMS = {"insta": "📷 Instagram", "linkedin": "💼 LinkedIn", "twitter": "🐦 Twitter"}


def render() -> None:
    sns.header("📝 Content")
    content = load_content()
    if not content:
        sns.info("No content created yet.")
        return

    for item in content:
        status = item.get("validation_status", "pending")
        icon = {"passed": "✅", "failed": "❌", "revised": "✏️"}.get(status, "⏳")
        sns.subheader(f"{icon} Content {str(item.get('session_id', ''))[:8]}")
        sns.caption(f"Quality score: {item.get('quality_score', 0)}/100")
        sns.caption(f"News IDs: {item.get('news_ids', [])}")
        sns.divider()

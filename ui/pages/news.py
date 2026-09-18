"""News feed monitoring page."""

from __future__ import annotations

import streamlit as sns
from ui.data import load_news


def render() -> None:
    sns.header("📰 News Feed")
    news = load_news()
    if not news:
        sns.info("No news articles fetched yet.")
        return

    for article in news:
        with sns.container():
            cols = sns.columns([3, 1])
            with cols[0]:
                sns.subheader(article.get("title", "")[:80])
                sns.caption(article.get("description", "")[:200])
                if article.get("url"):
                    sns.markdown(f"[🔗 Open Source]({article['url']})")
            with cols[1]:
                sns.caption(f"Category: {article.get('category', '?')}")
                sns.caption(f"Source: {article.get('source', '?')}")
            sns.divider()

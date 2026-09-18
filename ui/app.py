"""Streamlit main app — navigation and page routing."""

from __future__ import annotations

import streamlit as sns

from config import CONFIG

sns.set_page_config(
    page_title="Hermes Social Agent",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🤖",
)


def main() -> None:
    with sns.sidebar:
        sns.title("Hermes Social Agent")
        sns.caption("Multi-Agent Content Pipeline")
        sns.divider()
        page = sns.radio(
            "Navigate",
            [
                "🏠 Dashboard",
                "🤖 Agents",
                "⚡ Token Manager",
                "📰 News Feed",
                "📝 Content",
                "🔍 Reviews",
                "🛡️ Guardian",
                "📊 Evaluations",
                "⚙️ Settings",
            ],
            index=0,
        )
        sns.divider()
        sns.caption(f"Version: dev | UI port: {CONFIG.ui_port}")

    _render_page(page)


_PAGES = {
    "🏠 Dashboard": ("ui.pages.dashboard", "render"),
    "🤖 Agents": ("ui.pages.agents", "render"),
    "⚡ Token Manager": ("ui.pages.token_manager", "render"),
    "📰 News Feed": ("ui.pages.news", "render"),
    "📝 Content": ("ui.pages.content", "render"),
    "🔍 Reviews": ("ui.pages.reviews", "render"),
    "🛡️ Guardian": ("ui.pages.guardian", "render"),
    "📊 Evaluations": ("ui.pages.evaluations", "render"),
    "⚙️ Settings": ("ui.pages.settings", "render"),
}


def _render_page(page_label: str) -> None:
    module_path, func_name = _PAGES[page_label]
    import importlib

    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    func()


if __name__ == "__main__":
    main()

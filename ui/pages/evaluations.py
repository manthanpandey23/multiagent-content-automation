"""Evaluations reporting page."""

from __future__ import annotations

import streamlit as sns
from ui.data import load_evals
from ui.components.charts import bar_chart, line_chart


def render() -> None:
    sns.header("📊 Evaluations")
    evals = load_evals()
    if not evals:
        sns.info("No evaluation reports yet. Run the pipeline to generate scores.")
        return

    latest = evals[0]
    sns.subheader("Latest Evaluation")
    col1, col2 = sns.columns(2)
    with col1:
        sns.metric("Overall Score", f"{latest.get('overall_score', 0)}/100")
    with col2:
        sns.metric("Type", latest.get("eval_type", "run"))

    category_scores: dict = latest.get("category_scores", {})
    if category_scores:
        names = list(category_scores.keys())
        scores = [float(v) for v in category_scores.values()]
        bar_chart("Category Scores", names, scores)

    sns.subheader("Historical Scores")
    if len(evals) > 1:
        dates = [e.get("created_at", "").split("T")[0] if isinstance(e.get("created_at"), str) else str(e.get("created_at")) for e in evals]
        scores = [float(e.get("overall_score", 0)) for e in evals]
        line_chart("Overall Score Trend", dates, scores)

    sns.subheader("Recommendations")
    for rec in latest.get("recommendations", []):
        sns.caption(f"• {rec}")

"""Shared UI chart components (Streamlit native + Plotly)."""

from __future__ import annotations

from typing import Iterable

import plotly.graph_objects as go
import streamlit as sns
import pandas as pd


def bar_chart(title: str, labels: list[str], values: list[float], color: str = "#0077cc") -> None:
    df = pd.DataFrame({"label": labels, "value": values})
    fig = go.Figure(go.Bar(x=df["label"], y=df["value"], marker_color=color))
    fig.update_layout(title=title, xaxis_title="Label", yaxis_title="Value")
    sns.plotly_chart(fig, use_container_width=True)


def line_chart(title: str, dates: list[str], values: list[float]) -> None:
    fig = go.Figure(go.Scatter(x=dates, y=values, mode="lines+markers", line=dict(color="#0077cc")))
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Value")
    sns.plotly_chart(fig, use_container_width=True)


def pie_chart(title: str, labels: list[str], values: list[float]) -> None:
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.4))
    fig.update_layout(title=title)
    sns.plotly_chart(fig, use_container_width=True)


def score_gauge(title: str, score: float, max_score: float = 100) -> None:
    color = "green" if score >= 75 else ("orange" if score >= 50 else "red")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title},
        gauge={"axis": {"range": [0, max_score]}, "color": color},
    ))
    sns.plotly_chart(fig, use_container_width=True)

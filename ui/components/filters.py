"""Shared UI filter components."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as sns


def date_range_filter(label: str = "Date range") -> tuple[datetime, datetime]:
    periods = {
        "Today": "today",
        "Yesterday": "yesterday",
        "Last 7 Days": "7d",
        "Last 30 Days": "30d",
        "Custom Range": "custom",
    }
    choice = sns.sidebar.selectbox(label, list(periods.keys()), index=2)
    today = datetime.now().date()
    if choice == "Today":
        return datetime.combine(today, datetime.min.time()), datetime.combine(today, datetime.max.time())
    if choice == "Yesterday":
        yesterday = today - timedelta(days=1)
        return datetime.combine(yesterday, datetime.min.time()), datetime.combine(yesterday, datetime.max.time())
    if choice == "Last 7 Days":
        return datetime.combine(today - timedelta(days=7), datetime.min.time()), datetime.combine(today, datetime.max.time())
    if choice == "Last 30 Days":
        return datetime.combine(today - timedelta(days=30), datetime.min.time()), datetime.combine(today, datetime.max.time())
    start = sns.sidebar.date_input("Start date", today - timedelta(days=7))
    end = sns.sidebar.date_input("End date", today)
    return datetime.combine(start, datetime.min.time()), datetime.combine(end, datetime.max.time())


def entity_filter(label: str, options: list[str]) -> str:
    return sns.sidebar.selectbox(label, options, index=0)

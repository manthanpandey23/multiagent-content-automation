"""Shared data access helpers for the Streamlit dashboard."""

from __future__ import annotations

import streamlit as sns
from config import CONFIG
from utils.logger import get_logger

log = get_logger("ui_data")


def get_db_session():
    """Return a SQLAlchemy session or None if the DB is unavailable."""
    try:
        from db.connection import get_db

        with get_db() as db:
            return db
    except Exception as exc:
        log.warning("ui_db_unavailable", error=str(exc))
        return None


def get_orchestrator():
    """Return a lightweight orchestrator instance for live data."""
    try:
        from pipeline import PipelineOrchestrator

        return PipelineOrchestrator()
    except Exception as exc:
        log.warning("ui_orchestrator_unavailable", error=str(exc))
        return None


def load_sessions() -> list[dict]:
    db = get_db_session()
    if db is None:
        orch = get_orchestrator()
        if orch:
            return [s.model_dump() for s in orch._sessions.values()]
        return []
    try:
        from db.repositories import PipelineRepo

        # Use a raw query since PipelineRepo needs a session
        with db as session:
            rows = session.execute(
                "SELECT * FROM pipeline_state ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        log.warning("load_sessions_failed", error=str(exc))
        return []


def load_news() -> list[dict]:
    db = get_db_session()
    if db is None:
        return []
    try:
        rows = db.execute(
            "SELECT * FROM news_articles ORDER BY fetched_at DESC LIMIT 30"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def load_content() -> list[dict]:
    db = get_db_session()
    if db is None:
        return []
    try:
        rows = db.execute(
            "SELECT * FROM social_content ORDER BY created_at DESC LIMIT 30"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def load_reviews() -> list[dict]:
    db = get_db_session()
    if db is None:
        return []
    try:
        rows = db.execute(
            "SELECT * FROM review_records ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def load_guardian_alerts() -> list[dict]:
    db = get_db_session()
    if db is None:
        return []
    try:
        rows = db.execute(
            "SELECT * FROM guardian_alerts ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def load_evals() -> list[dict]:
    db = get_db_session()
    if db is None:
        return []
    try:
        rows = db.execute(
            "SELECT * FROM eval_results ORDER BY created_at DESC LIMIT 30"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def load_token_usage() -> list[dict]:
    db = get_db_session()
    if db is None:
        return []
    try:
        rows = db.execute(
            "SELECT * FROM token_usage ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []

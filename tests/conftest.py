"""Shared test fixtures and configuration."""

from __future__ import annotations

import os
import sys

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def pytest_configure(config):
    os.environ.setdefault("OPENAI_API_KEY", "test")


# Optional: in-memory SQLite for DB repo tests
import pytest


@pytest.fixture
def sqlite_db(monkeypatch):
    """Provide an in-memory SQLite session for repository tests."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    from db.orm import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if hasattr(dbapi_connection, "execute"):
            try:
                dbapi_connection.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()

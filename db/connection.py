"""Database connection manager using SQLAlchemy 2.0."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from config import CONFIG
from utils.logger import get_logger

log = get_logger("db")

_engine = None
_SessionLocal: sessionmaker | None = None


def _make_url() -> str:
    return CONFIG.database_url


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    url = _make_url()
    log.info("initializing_database_engine", url=url.split("@")[0] + "@***")
    _engine = create_engine(
        url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False,
    )
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return _SessionLocal


class Database:
    """Thin wrapper exposing engine and session factory."""

    def __init__(self) -> None:
        self.engine = get_engine()
        self.SessionLocal = get_session_factory()

    @contextmanager
    def session(self) -> Iterator[Session]:
        db: Session = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


@contextmanager
def get_db() -> Iterator[Session]:
    factory = get_session_factory()
    db: Session = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined in the ORM registry."""
    from db.orm import Base

    engine = get_engine()
    Base.metadata.create_all(engine)
    log.info("database_tables_initialized")


def ping() -> bool:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.error("database_ping_failed", error=str(exc))
        return False

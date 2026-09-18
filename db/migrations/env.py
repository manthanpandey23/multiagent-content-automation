"""Alembic migration environment."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from config import CONFIG
from db.orm import Base

config = os.environ.get("ALEMBIC_CONFIG", "")
target_metadata = Base.metadata


def get_url() -> str:
    return CONFIG.database_url


def run_migrations_offline() -> None:
    url = get_url()
    fileConfig(config_file=config) if config else None
    context = __import__("alembic.runtime.context", fromlist=["MigrationContext"]).MigrationContext
    ctx = context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with ctx.begin_transaction():
        ctx.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context = __import__("alembic.runtime.context", fromlist=["MigrationContext"]).MigrationContext
        ctx = context.configure(connection=connection, target_metadata=target_metadata)
        with ctx.begin_transaction():
            ctx.run_migrations()


from alembic import context  # noqa: E402

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Structured logging utility."""

from __future__ import annotations

import sys
import warnings

# On Windows the default console encoding is often cp1252, which breaks on
# emoji / unicode that appear in Telegram messages and Guardian alerts.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Belt-and-suspenders: suppress any stray utcnow() deprecation.
warnings.filterwarnings("ignore", message=".*utcnow.*", category=DeprecationWarning)

import structlog

_LOGGER_CONFIGURED = False


def _configure() -> structlog.BoundLogger:
    global _LOGGER_CONFIGURED
    if not _LOGGER_CONFIGURED:
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),
        )
        _LOGGER_CONFIGURED = True
    return structlog.get_logger()


def get_logger(name: str = "hermes") -> structlog.BoundLogger:
    return _configure().bind(component=name)

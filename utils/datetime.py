"""Timezone-aware utility helpers.

Provides :func:`utcnow` as a drop-in replacement for the deprecated
``datetime.utcnow()`` (Python 3.14+).  Returns a naive UTC datetime to
preserve compatibility with existing storage layers.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime.

    Equivalent to the old ``datetime.utcnow()`` but without the
    deprecation warning in Python 3.14+.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utcnow_iso() -> str:
    """ISO-format UTC timestamp string."""
    return utcnow().isoformat()

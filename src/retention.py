"""Filter entries to a rolling retention window."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import ChangeEntry

_DEFAULT_DAYS = 90  # ~3 months


def filter_recent(
    entries: list[ChangeEntry],
    *,
    days: int = _DEFAULT_DAYS,
) -> list[ChangeEntry]:
    """Return only entries published within the last *days* days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [e for e in entries if e.published >= cutoff]

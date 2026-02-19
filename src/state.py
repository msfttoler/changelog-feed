"""SQLite-backed state store for deduplication.

Persists the (source, item_id) pairs that have already been processed so
that each run only acts on genuinely new items.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS seen_items (
    source  TEXT NOT NULL,
    item_id TEXT NOT NULL,
    PRIMARY KEY (source, item_id)
)
"""


class StateStore:
    """Persistent store that tracks which items have already been processed."""

    def __init__(self, db_path: str | Path = ".changelog_feed_state.db") -> None:
        self._path = str(db_path)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_seen(self, source: str, item_id: str) -> bool:
        """Return True if this (source, item_id) was already processed."""
        row = self._conn.execute(
            "SELECT 1 FROM seen_items WHERE source = ? AND item_id = ?",
            (source, item_id),
        ).fetchone()
        return row is not None

    def mark_seen(self, source: str, item_id: str) -> None:
        """Record (source, item_id) as processed."""
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_items (source, item_id) VALUES (?, ?)",
            (source, item_id),
        )
        self._conn.commit()

    def mark_seen_batch(self, items: list[tuple[str, str]]) -> None:
        """Record multiple (source, item_id) pairs as processed."""
        self._conn.executemany(
            "INSERT OR IGNORE INTO seen_items (source, item_id) VALUES (?, ?)",
            items,
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def __enter__(self) -> "StateStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

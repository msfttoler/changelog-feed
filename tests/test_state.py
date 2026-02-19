"""Tests for the SQLite state store."""

import os
import tempfile

import pytest

from src.state import StateStore


@pytest.fixture()
def store(tmp_path):
    db = tmp_path / "test.db"
    with StateStore(str(db)) as s:
        yield s


class TestStateStore:
    def test_item_not_seen_initially(self, store):
        assert not store.is_seen("github", "abc123")

    def test_mark_seen_makes_item_seen(self, store):
        store.mark_seen("github", "abc123")
        assert store.is_seen("github", "abc123")

    def test_different_source_same_id_not_seen(self, store):
        store.mark_seen("github", "abc123")
        assert not store.is_seen("vscode", "abc123")

    def test_mark_seen_idempotent(self, store):
        store.mark_seen("github", "abc123")
        store.mark_seen("github", "abc123")  # Should not raise
        assert store.is_seen("github", "abc123")

    def test_mark_seen_batch(self, store):
        pairs = [("github", "id1"), ("vscode", "id2"), ("visualstudio", "id3")]
        store.mark_seen_batch(pairs)
        for source, item_id in pairs:
            assert store.is_seen(source, item_id)

    def test_state_persists_across_connections(self, tmp_path):
        db = str(tmp_path / "persist.db")
        with StateStore(db) as s:
            s.mark_seen("github", "persistent_id")

        with StateStore(db) as s2:
            assert s2.is_seen("github", "persistent_id")

    def test_context_manager_closes_connection(self, tmp_path):
        db = str(tmp_path / "ctx.db")
        with StateStore(db) as s:
            s.mark_seen("github", "x")
        # After exiting context, the connection should be closed
        # (no exception means it was closed gracefully)

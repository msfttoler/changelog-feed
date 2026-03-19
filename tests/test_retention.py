"""Unit tests for retention filter."""

from datetime import datetime, timedelta, timezone

from src.models import ChangeEntry
from src.retention import filter_recent


def _make_entry(days_ago: int, **overrides):
    pub = datetime.now(timezone.utc) - timedelta(days=days_ago)
    defaults = {
        "id": f"entry-{days_ago}",
        "source": "github",
        "title": f"Entry from {days_ago} days ago",
        "description": "Test",
        "link": f"https://example.com/{days_ago}",
        "published": pub,
    }
    defaults.update(overrides)
    return ChangeEntry(**defaults)


class TestFilterRecent:
    def test_keeps_recent_entries(self):
        entries = [_make_entry(1), _make_entry(30), _make_entry(60)]
        result = filter_recent(entries)
        assert len(result) == 3

    def test_removes_old_entries(self):
        entries = [_make_entry(1), _make_entry(100), _make_entry(200)]
        result = filter_recent(entries)
        assert len(result) == 1
        assert result[0].id == "entry-1"

    def test_boundary_89_days(self):
        entry = _make_entry(89)
        result = filter_recent([entry])
        assert len(result) == 1

    def test_boundary_91_days_excluded(self):
        entry = _make_entry(91)
        result = filter_recent([entry])
        assert len(result) == 0

    def test_boundary_92_days(self):
        entry = _make_entry(92)
        result = filter_recent([entry])
        assert len(result) == 0

    def test_empty_input(self):
        assert filter_recent([]) == []

    def test_all_old(self):
        entries = [_make_entry(100), _make_entry(200), _make_entry(365)]
        result = filter_recent(entries)
        assert len(result) == 0

    def test_custom_days(self):
        entries = [_make_entry(10), _make_entry(25), _make_entry(35)]
        result = filter_recent(entries, days=30)
        assert len(result) == 2

    def test_preserves_order(self):
        entries = [_make_entry(60), _make_entry(10), _make_entry(30)]
        result = filter_recent(entries)
        assert [e.id for e in result] == ["entry-60", "entry-10", "entry-30"]

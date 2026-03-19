"""Unit tests for summarizer module."""

from datetime import datetime, timezone

from src.models import ChangeEntry
from src.summarizer import _heuristic_summary, add_summaries


def _make_entry(title="Test", description="Desc", **overrides):
    defaults = {
        "id": overrides.pop("id", "t1"),
        "source": "github",
        "title": title,
        "description": description,
        "link": "https://example.com",
        "published": datetime(2025, 6, 1, tzinfo=timezone.utc),
        "score": overrides.pop("score", 50),
    }
    defaults.update(overrides)
    return ChangeEntry(**defaults)


class TestHeuristicSummary:
    def test_security_match(self):
        e = _make_entry(title="Security vulnerability disclosed")
        result = _heuristic_summary(e)
        assert "security" in result.lower() or "Security" in result

    def test_breaking_change_match(self):
        e = _make_entry(description="This is a breaking change in v2 API")
        result = _heuristic_summary(e)
        assert "breaking" in result.lower() or "Breaking" in result

    def test_copilot_match(self):
        e = _make_entry(title="GitHub Copilot agent mode improvements")
        result = _heuristic_summary(e)
        assert "ai" in result.lower() or "copilot" in result.lower()

    def test_ga_match(self):
        e = _make_entry(title="Feature X now available for all")
        result = _heuristic_summary(e)
        assert "general-availability" in result.lower() or "production" in result.lower()

    def test_preview_match(self):
        e = _make_entry(title="New preview feature released")
        result = _heuristic_summary(e)
        assert "preview" in result.lower() or "beta" in result.lower() or "testing" in result.lower()

    def test_performance_match(self):
        e = _make_entry(title="Faster build times")
        result = _heuristic_summary(e)
        assert "performance" in result.lower() or "faster" in result.lower()

    def test_bugfix_match(self):
        e = _make_entry(title="Bug fix for login issue")
        result = _heuristic_summary(e)
        assert "bug" in result.lower() or "fix" in result.lower() or "issue" in result.lower()

    def test_fallback(self):
        e = _make_entry(title="Some random update", description="Nothing special")
        result = _heuristic_summary(e)
        assert "notable" in result.lower() or "changelog" in result.lower()

    def test_tags_contribute(self):
        e = _make_entry(title="Update", description="Plain", tags=["security"])
        result = _heuristic_summary(e)
        assert "security" in result.lower() or "Security" in result


class TestAddSummaries:
    def test_marks_top_8_as_highlighted(self):
        entries = [_make_entry(id=f"e{i}", score=100 - i) for i in range(12)]
        result = add_summaries(entries)
        highlighted = [e for e in result if e.highlight]
        assert len(highlighted) == 8

    def test_non_top_entries_not_highlighted(self):
        entries = [_make_entry(id=f"e{i}", score=100 - i) for i in range(12)]
        result = add_summaries(entries)
        non_highlighted = [e for e in result if not e.highlight]
        assert len(non_highlighted) == 4

    def test_highlighted_entries_have_summary(self):
        entries = [_make_entry(id=f"e{i}", score=100 - i) for i in range(5)]
        result = add_summaries(entries)
        for e in result:
            if e.highlight:
                assert e.ai_summary != ""

    def test_preserves_entry_count(self):
        entries = [_make_entry(id=f"e{i}") for i in range(20)]
        result = add_summaries(entries)
        assert len(result) == 20

    def test_fewer_than_max_highlights(self):
        entries = [_make_entry(id=f"e{i}") for i in range(3)]
        result = add_summaries(entries)
        highlighted = [e for e in result if e.highlight]
        assert len(highlighted) == 3

    def test_empty_entries(self):
        result = add_summaries([])
        assert result == []

    def test_uses_heuristic_without_openai(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        entries = [
            _make_entry(id="sec1", title="Security vulnerability found", score=90),
            _make_entry(id="cop1", title="GitHub Copilot new feature", score=80),
        ]
        result = add_summaries(entries)
        # Should still have summaries (heuristic fallback)
        for e in result:
            assert e.ai_summary != ""

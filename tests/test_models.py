"""Unit tests for ChangeEntry model."""

from datetime import datetime, timezone

from src.models import ChangeEntry


def _make_entry(**overrides):
    defaults = {
        "id": "abc123",
        "source": "github",
        "title": "Test entry",
        "description": "A test description",
        "link": "https://example.com/1",
        "published": datetime(2025, 6, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return ChangeEntry(**defaults)


class TestChangeEntryDefaults:
    def test_tags_default_empty(self):
        e = _make_entry()
        assert e.tags == []

    def test_is_copilot_default_false(self):
        e = _make_entry()
        assert e.is_copilot is False

    def test_score_default_zero(self):
        e = _make_entry()
        assert e.score == 0

    def test_severity_default_low(self):
        e = _make_entry()
        assert e.severity == "low"

    def test_ai_summary_default_empty(self):
        e = _make_entry()
        assert e.ai_summary == ""

    def test_highlight_default_false(self):
        e = _make_entry()
        assert e.highlight is False


class TestChangeEntryFields:
    def test_all_fields_set(self):
        e = _make_entry(
            tags=["copilot", "security"],
            is_copilot=True,
            score=85,
            severity="critical",
            ai_summary="Important update",
            highlight=True,
        )
        assert e.tags == ["copilot", "security"]
        assert e.is_copilot is True
        assert e.score == 85
        assert e.severity == "critical"
        assert e.ai_summary == "Important update"
        assert e.highlight is True

    def test_published_datetime(self):
        pub = datetime(2025, 3, 15, 10, 30, tzinfo=timezone.utc)
        e = _make_entry(published=pub)
        assert e.published == pub


class TestChangeEntrySerialization:
    def test_model_dump_roundtrip(self):
        e = _make_entry(score=50, severity="high")
        data = e.model_dump(mode="json")
        assert data["id"] == "abc123"
        assert data["score"] == 50
        assert data["severity"] == "high"
        assert isinstance(data["published"], str)

    def test_model_copy_update(self):
        e = _make_entry()
        updated = e.model_copy(update={"score": 75, "severity": "critical"})
        assert updated.score == 75
        assert updated.severity == "critical"
        # Original unchanged
        assert e.score == 0

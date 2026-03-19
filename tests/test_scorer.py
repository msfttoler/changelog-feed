"""Unit tests for scorer module."""

from datetime import datetime, timezone

from src.models import ChangeEntry
from src.scorer import score_entry


def _make_entry(**overrides):
    defaults = {
        "id": "test1",
        "source": "github",
        "title": "Test entry",
        "description": "A basic description",
        "link": "https://example.com",
        "published": datetime(2025, 6, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return ChangeEntry(**defaults)


class TestScoreEntry:
    def test_base_score_no_keywords(self):
        e = score_entry(_make_entry(title="Minor tweak", description="Small UI fix"))
        assert e.score == 10
        assert e.severity == "low"

    def test_security_keywords(self):
        e = score_entry(_make_entry(title="Security vulnerability patch"))
        assert e.score >= 50
        assert e.severity in ("high", "critical")

    def test_breaking_change_keywords(self):
        e = score_entry(_make_entry(title="Breaking change in API v2"))
        assert e.score >= 45

    def test_copilot_keywords(self):
        e = score_entry(_make_entry(title="GitHub Copilot new feature"))
        # copilot (15) + new feature (10) + base (10) = 35
        assert e.score == 35
        assert e.severity == "medium"

    def test_combined_keywords(self):
        e = score_entry(
            _make_entry(
                title="Security advisory for Copilot",
                description="Breaking change with deprecation",
            )
        )
        # security (40) + breaking (35) + copilot (15) + base (10) = 100
        assert e.score == 100
        assert e.severity == "critical"

    def test_score_capped_at_100(self):
        e = score_entry(
            _make_entry(
                title="Security vulnerability breaking change Copilot introducing performance",
                description="bug fix",
            )
        )
        assert e.score <= 100

    def test_tags_contribute_to_scoring(self):
        e = score_entry(_make_entry(tags=["security", "copilot"]))
        assert e.score > 10

    def test_description_contributes(self):
        e = score_entry(
            _make_entry(title="Update", description="Fixes a security vulnerability")
        )
        assert e.score >= 50


class TestSeverityBands:
    def test_low(self):
        e = score_entry(_make_entry(title="Misc notes"))
        assert e.severity == "low"

    def test_medium(self):
        e = score_entry(_make_entry(title="New feature announcing a preview"))
        # "new feature" not present but "announcing" (10) + "preview" isn't in this list
        # Actually: "announcing" matches "introducing/now available/announcing" = 10 → total 20
        # Let's use copilot which gives 25
        e = score_entry(_make_entry(title="Copilot update"))
        assert e.severity == "medium"

    def test_high(self):
        e = score_entry(
            _make_entry(
                title="Copilot breaking change deprecation notice",
                description="End of life for old API",
            )
        )
        # copilot(15) + breaking(35) + base(10) = 60 → high
        assert e.severity == "high"

    def test_critical(self):
        e = score_entry(
            _make_entry(
                title="Security vulnerability CVE-2025-1234",
                description="Breaking change with deprecation of old auth",
            )
        )
        # security(40) + breaking(35) + base(10) = 85 → critical
        assert e.severity == "critical"


class TestScoreEntryImmutability:
    def test_original_unchanged(self):
        orig = _make_entry()
        scored = score_entry(orig)
        assert orig.score == 0
        assert scored.score > 0

    def test_returns_new_instance(self):
        orig = _make_entry()
        scored = score_entry(orig)
        assert orig is not scored

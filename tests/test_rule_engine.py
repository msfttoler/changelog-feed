"""Tests for the deterministic rule engine."""

from datetime import datetime, timezone

import pytest

from src.models import ChangeItem, ProductArea, RuleDecision, Source
from src import rule_engine


def make_item(title: str = "", description: str = "") -> ChangeItem:
    return ChangeItem(
        id="test",
        source=Source.GITHUB,
        product_area=ProductArea.OTHER,
        title=title,
        description=description,
        link="https://example.com",
        published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        raw_text=f"{title} {description}",
    )


class TestAlwaysPost:
    def test_security_in_title(self):
        item = make_item(title="Security fix for OAuth flow")
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST

    def test_cve_in_description(self):
        item = make_item(title="Patch released", description="Fixes cve-2024-1234")
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST

    def test_breaking_change(self):
        item = make_item(title="Breaking change: API v2 deprecated")
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST

    def test_deprecation(self):
        item = make_item(title="Feature deprecation notice")
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST

    def test_retirement(self):
        item = make_item(title="Retirement of legacy connector")
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST

    def test_end_of_life(self):
        item = make_item(description="This feature reaches end of life in Q4")
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST

    def test_vulnerability(self):
        item = make_item(title="Critical vulnerability patched")
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST

    def test_enterprise_policy(self):
        item = make_item(title="New enterprise policy controls added")
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST

    def test_case_insensitive(self):
        item = make_item(title="SECURITY: important update")
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST


class TestNeverPost:
    def test_emoji_in_title(self):
        item = make_item(title="New emoji pack added to comments")
        assert rule_engine.evaluate(item) == RuleDecision.NEVER_POST

    def test_ui_polish_in_title(self):
        item = make_item(title="UI polish for the settings page")
        assert rule_engine.evaluate(item) == RuleDecision.NEVER_POST

    def test_typo_fix_in_title(self):
        item = make_item(title="Typo fix in welcome message")
        assert rule_engine.evaluate(item) == RuleDecision.NEVER_POST

    def test_dark_mode_in_title(self):
        item = make_item(title="Dark mode improvements for editor")
        assert rule_engine.evaluate(item) == RuleDecision.NEVER_POST

    def test_never_post_only_in_description_defers_to_ai(self):
        # A never-post keyword in the *description only* (not title) defers to AI
        item = make_item(title="New editor feature", description="includes some emoji packs")
        assert rule_engine.evaluate(item) == RuleDecision.DEFER_TO_AI


class TestDeferToAI:
    def test_neutral_item(self):
        item = make_item(title="Improved auto-complete for Python", description="Better IntelliSense")
        assert rule_engine.evaluate(item) == RuleDecision.DEFER_TO_AI

    def test_copilot_improvement(self):
        item = make_item(title="Copilot chat now supports multi-file edits")
        assert rule_engine.evaluate(item) == RuleDecision.DEFER_TO_AI


class TestAlwaysPostOverridesNeverPost:
    def test_security_beats_emoji(self):
        # If a title mentions both security and emoji, ALWAYS_POST wins
        item = make_item(
            title="Security fix for emoji rendering vulnerability",
            description="Fixes a security issue",
        )
        assert rule_engine.evaluate(item) == RuleDecision.ALWAYS_POST

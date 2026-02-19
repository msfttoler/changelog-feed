"""Tests for the core data models."""

from datetime import datetime, timezone

import pytest

from src.models import (
    ChangeItem,
    ClassificationResult,
    CSARelevance,
    CustomerImpact,
    ProductArea,
    RuleDecision,
    ScoredItem,
    Source,
)


def make_item(**kwargs) -> ChangeItem:
    defaults = dict(
        id="abc123",
        source=Source.GITHUB,
        product_area=ProductArea.COPILOT,
        title="Test change",
        description="A test change description",
        link="https://example.com/changelog/1",
        published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        raw_text="Full raw text of the change",
    )
    defaults.update(kwargs)
    return ChangeItem(**defaults)


def make_classification(**kwargs) -> ClassificationResult:
    defaults = dict(
        csa_relevance=CSARelevance.HIGH,
        why_it_matters="Impacts enterprise Copilot adoption",
        customer_impact=CustomerImpact.BROAD,
        conversation_trigger=True,
        categories=["copilot", "enterprise"],
        confidence=0.9,
    )
    defaults.update(kwargs)
    return ClassificationResult(**defaults)


class TestChangeItem:
    def test_required_fields(self):
        item = make_item()
        assert item.id == "abc123"
        assert item.source == Source.GITHUB
        assert item.product_area == ProductArea.COPILOT
        assert item.raw_category is None

    def test_optional_raw_category(self):
        item = make_item(raw_category="Copilot")
        assert item.raw_category == "Copilot"

    def test_source_enum_values(self):
        assert Source.GITHUB.value == "github"
        assert Source.VSCODE.value == "vscode"
        assert Source.VISUALSTUDIO.value == "visualstudio"

    def test_product_area_enum_values(self):
        assert ProductArea.COPILOT.value == "copilot"
        assert ProductArea.SECURITY.value == "security"
        assert ProductArea.DEVCONTAINERS.value == "devcontainers"


class TestClassificationResult:
    def test_confidence_bounds(self):
        # Valid bounds
        clf = make_classification(confidence=0.0)
        assert clf.confidence == 0.0
        clf = make_classification(confidence=1.0)
        assert clf.confidence == 1.0

    def test_confidence_out_of_range(self):
        with pytest.raises(Exception):
            make_classification(confidence=1.5)
        with pytest.raises(Exception):
            make_classification(confidence=-0.1)

    def test_enum_values(self):
        assert CSARelevance.HIGH.value == "high"
        assert CSARelevance.MEDIUM.value == "medium"
        assert CSARelevance.LOW.value == "low"
        assert CustomerImpact.BROAD.value == "broad"
        assert CustomerImpact.SITUATIONAL.value == "situational"


class TestScoredItem:
    def test_defaults(self):
        item = make_item()
        scored = ScoredItem(item=item)
        assert scored.rule_decision == RuleDecision.DEFER_TO_AI
        assert scored.classification is None
        assert scored.should_post is False

    def test_with_classification(self):
        item = make_item()
        clf = make_classification()
        scored = ScoredItem(item=item, classification=clf, should_post=True)
        assert scored.should_post is True
        assert scored.classification.csa_relevance == CSARelevance.HIGH

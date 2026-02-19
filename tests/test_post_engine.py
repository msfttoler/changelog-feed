"""Tests for the PostDecisionEngine."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.models import (
    ChangeItem,
    ClassificationResult,
    CSARelevance,
    CustomerImpact,
    ProductArea,
    RuleDecision,
    Source,
)
from src.post_engine import PostDecisionEngine, _relevance_rank


def make_item(title: str = "Test change", description: str = "") -> ChangeItem:
    return ChangeItem(
        id="test",
        source=Source.GITHUB,
        product_area=ProductArea.COPILOT,
        title=title,
        description=description,
        link="https://example.com",
        published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        raw_text="raw",
    )


def make_classifier(relevance: CSARelevance) -> MagicMock:
    """Return a mock AIClassifier that always returns the given relevance."""
    clf_result = ClassificationResult(
        csa_relevance=relevance,
        why_it_matters="Test reason",
        customer_impact=CustomerImpact.BROAD,
        conversation_trigger=True,
        categories=["test"],
        confidence=0.9,
    )
    mock = MagicMock()
    mock.classify_batch.return_value = [clf_result]
    return mock


class TestRelevanceRank:
    def test_ordering(self):
        assert _relevance_rank(CSARelevance.LOW) < _relevance_rank(CSARelevance.MEDIUM)
        assert _relevance_rank(CSARelevance.MEDIUM) < _relevance_rank(CSARelevance.HIGH)


class TestPostDecisionEngine:
    def test_always_post_rule_posts_without_classifier(self):
        engine = PostDecisionEngine(classifier=None)
        item = make_item(title="Security fix for authentication")
        scored_items = engine.evaluate_batch([item])
        assert len(scored_items) == 1
        assert scored_items[0].should_post is True
        assert scored_items[0].rule_decision == RuleDecision.ALWAYS_POST

    def test_never_post_rule_skips_without_classifier(self):
        engine = PostDecisionEngine(classifier=None)
        item = make_item(title="New emoji pack added")
        scored_items = engine.evaluate_batch([item])
        assert scored_items[0].should_post is False
        assert scored_items[0].rule_decision == RuleDecision.NEVER_POST

    def test_defer_to_ai_high_relevance_posts(self, monkeypatch):
        monkeypatch.setenv("MIN_RELEVANCE", "high")
        mock_clf = make_classifier(CSARelevance.HIGH)
        engine = PostDecisionEngine(classifier=mock_clf)
        item = make_item(title="Improved IntelliSense for Python")
        scored_items = engine.evaluate_batch([item])
        assert scored_items[0].should_post is True

    def test_defer_to_ai_low_relevance_does_not_post(self, monkeypatch):
        monkeypatch.setenv("MIN_RELEVANCE", "high")
        mock_clf = make_classifier(CSARelevance.LOW)
        engine = PostDecisionEngine(classifier=mock_clf)
        item = make_item(title="Minor syntax highlighting update")
        scored_items = engine.evaluate_batch([item])
        assert scored_items[0].should_post is False

    def test_defer_to_ai_medium_posts_when_threshold_is_medium(self, monkeypatch):
        monkeypatch.setenv("MIN_RELEVANCE", "medium")
        mock_clf = make_classifier(CSARelevance.MEDIUM)
        engine = PostDecisionEngine(classifier=mock_clf)
        item = make_item(title="New debugger feature")
        scored_items = engine.evaluate_batch([item])
        assert scored_items[0].should_post is True

    def test_no_classifier_defers_to_ai_item_does_not_post(self):
        engine = PostDecisionEngine(classifier=None)
        item = make_item(title="Better autocomplete suggestions")
        scored_items = engine.evaluate_batch([item])
        assert scored_items[0].rule_decision == RuleDecision.DEFER_TO_AI
        assert scored_items[0].should_post is False

    def test_classifier_called_only_for_deferred_items(self, monkeypatch):
        monkeypatch.setenv("MIN_RELEVANCE", "high")
        mock_clf = MagicMock()
        mock_clf.classify_batch.return_value = [
            ClassificationResult(
                csa_relevance=CSARelevance.HIGH,
                why_it_matters="test",
                customer_impact=CustomerImpact.BROAD,
                conversation_trigger=True,
                categories=[],
                confidence=0.9,
            )
        ]
        engine = PostDecisionEngine(classifier=mock_clf)
        # One security item (ALWAYS_POST) + one neutral item (DEFER_TO_AI)
        items = [
            make_item(title="Security patch for CVE-2024-1234"),
            make_item(title="Improved code completion"),
        ]
        engine.evaluate_batch(items)
        # Classifier should only be called for the neutral item
        mock_clf.classify_batch.assert_called_once()
        _, call_args = mock_clf.classify_batch.call_args[0][0], None
        # The batch passed should contain only the neutral item (not the security one)
        batch = mock_clf.classify_batch.call_args[0][0]
        assert len(batch) == 1
        assert "Improved code completion" in batch[0].title

    def test_evaluate_batch_returns_scored_items_in_order(self, monkeypatch):
        monkeypatch.setenv("MIN_RELEVANCE", "high")
        mock_clf = MagicMock()
        mock_clf.classify_batch.return_value = [
            ClassificationResult(
                csa_relevance=CSARelevance.LOW,
                why_it_matters="low",
                customer_impact=CustomerImpact.NONE,
                conversation_trigger=False,
                categories=[],
                confidence=0.1,
            ),
            ClassificationResult(
                csa_relevance=CSARelevance.HIGH,
                why_it_matters="high",
                customer_impact=CustomerImpact.BROAD,
                conversation_trigger=True,
                categories=[],
                confidence=0.9,
            ),
        ]
        engine = PostDecisionEngine(classifier=mock_clf)
        items = [
            make_item(title="Minor autocomplete tweak"),
            make_item(title="New Actions workflow feature"),
        ]
        scored = engine.evaluate_batch(items)
        assert len(scored) == 2
        assert scored[0].should_post is False
        assert scored[1].should_post is True

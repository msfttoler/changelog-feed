"""Post decision engine.

Combines the rule engine result and the AI classification to determine
whether a :class:`~src.models.ChangeItem` should be posted to Teams.

Decision logic
--------------
1. Rule engine says ALWAYS_POST → post (no AI veto).
2. Rule engine says NEVER_POST  → skip (no AI override).
3. Rule engine says DEFER_TO_AI → post if AI relevance ≥ threshold.

The relevance threshold is configurable and defaults to "high", meaning
only items the AI rates as high-relevance reach the channel.
"""

from __future__ import annotations

import logging
import os

from src.classifier import AIClassifier
from src.models import ChangeItem, CSARelevance, RuleDecision, ScoredItem
from src import rule_engine

logger = logging.getLogger(__name__)

# Ordered relevance levels from lowest to highest
_RELEVANCE_ORDER: list[str] = [
    CSARelevance.LOW.value,
    CSARelevance.MEDIUM.value,
    CSARelevance.HIGH.value,
]


def _relevance_rank(level: CSARelevance) -> int:
    try:
        return _RELEVANCE_ORDER.index(level.value)
    except ValueError:
        return 0


def _min_relevance_rank() -> int:
    raw = os.environ.get("MIN_RELEVANCE", "high").lower()
    try:
        return _RELEVANCE_ORDER.index(raw)
    except ValueError:
        logger.warning("Invalid MIN_RELEVANCE value '%s'; defaulting to 'high'", raw)
        return _RELEVANCE_ORDER.index("high")


class PostDecisionEngine:
    """Applies rule + AI signals to decide which items to post.

    Parameters
    ----------
    classifier:
        An :class:`~src.classifier.AIClassifier` instance.  Pass ``None``
        to run in rule-only mode (useful when no AI credentials are
        available or for testing).
    """

    def __init__(self, classifier: AIClassifier | None = None) -> None:
        self._classifier = classifier

    def evaluate_batch(self, items: list[ChangeItem]) -> list[ScoredItem]:
        """Evaluate a list of items and return :class:`~src.models.ScoredItem` objects.

        Only items where AI is needed (DEFER_TO_AI) are sent to the classifier,
        reducing API calls for items already decided by the rule engine.
        """
        scored: list[ScoredItem] = []
        to_classify: list[tuple[int, ChangeItem]] = []

        # Phase 1: apply rule engine to all items
        for item in items:
            decision = rule_engine.evaluate(item)
            scored.append(
                ScoredItem(
                    item=item,
                    rule_decision=decision,
                )
            )

        # Phase 2: collect items that need AI classification
        for idx, s in enumerate(scored):
            if s.rule_decision == RuleDecision.DEFER_TO_AI and self._classifier is not None:
                to_classify.append((idx, s.item))

        # Phase 3: run AI classifier
        if to_classify:
            indices, ai_items = zip(*to_classify)
            classifications = self._classifier.classify_batch(list(ai_items))
            for idx, clf in zip(indices, classifications):
                scored[idx].classification = clf

        # Phase 4: apply post decision
        min_rank = _min_relevance_rank()
        for s in scored:
            s.should_post = self._decide(s, min_rank)

        return scored

    def _decide(self, scored: ScoredItem, min_rank: int) -> bool:
        """Return True if this item should be posted."""
        if scored.rule_decision == RuleDecision.ALWAYS_POST:
            return True
        if scored.rule_decision == RuleDecision.NEVER_POST:
            return False
        # DEFER_TO_AI
        if scored.classification is None:
            # No classifier configured – default to not posting
            return False
        return _relevance_rank(scored.classification.csa_relevance) >= min_rank

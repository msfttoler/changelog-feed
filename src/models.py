"""Normalized data models for the changelog-feed signal engine."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Source(str, Enum):
    """Platform source of the change item."""

    GITHUB = "github"
    VSCODE = "vscode"
    VISUALSTUDIO = "visualstudio"


class ProductArea(str, Enum):
    """High-level product area classification."""

    COPILOT = "copilot"
    ACTIONS = "actions"
    IDE = "ide"
    SECURITY = "security"
    DEVCONTAINERS = "devcontainers"
    ENTERPRISE = "enterprise"
    OTHER = "other"


class ChangeItem(BaseModel):
    """Normalized change item ingested from any source.

    This is the single internal schema that all ingestors produce.
    Having a canonical schema enables deterministic deduplication,
    repeatable AI decisions, and easy rule overrides.
    """

    id: str = Field(description="Stable unique identifier (source-scoped)")
    source: Source
    product_area: ProductArea
    title: str
    description: str
    link: str
    published_at: datetime
    raw_category: Optional[str] = Field(
        default=None, description="Original category string from the source feed"
    )
    raw_text: str = Field(description="Full paragraph or bullet text from the source")


class CSARelevance(str, Enum):
    """AI-assigned relevance level for a Cloud Solution Architect audience."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CustomerImpact(str, Enum):
    """Breadth of customer impact for a change item."""

    NONE = "none"
    SITUATIONAL = "situational"
    BROAD = "broad"


class ClassificationResult(BaseModel):
    """Structured AI classification output.

    AI supplies inputs (scoring + explanation) but does NOT decide
    what to post. That decision belongs to the PostDecisionEngine.
    """

    csa_relevance: CSARelevance
    why_it_matters: str = Field(description="One-sentence explanation for CSAs")
    customer_impact: CustomerImpact
    conversation_trigger: bool = Field(
        description="True if this item is likely to come up in customer conversations"
    )
    categories: list[str] = Field(
        description="Labels such as 'security', 'copilot', 'breaking-change'"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Classifier confidence 0-1")


class RuleDecision(str, Enum):
    """Outcome from the deterministic rule engine."""

    ALWAYS_POST = "always_post"
    NEVER_POST = "never_post"
    DEFER_TO_AI = "defer_to_ai"


class ScoredItem(BaseModel):
    """A normalized change item augmented with rule and AI decisions."""

    item: ChangeItem
    rule_decision: RuleDecision = RuleDecision.DEFER_TO_AI
    classification: Optional[ClassificationResult] = None
    should_post: bool = False

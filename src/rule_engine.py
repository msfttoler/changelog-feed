"""Deterministic rule engine for CSA relevance.

Before the AI classifier runs, hard rules decide whether an item should
*always* be posted or *never* be posted, regardless of the AI score.

This prevents:
  - "AI thought this looked cool so it spammed the channel"
  - High-stakes items (security fixes, breaking changes) being silently dropped
"""

from __future__ import annotations

from src.models import ChangeItem, RuleDecision

# ── Always-post keywords ─────────────────────────────────────────────────────
# Items containing any of these terms are posted unconditionally.

ALWAYS_POST_PATTERNS: list[str] = [
    "security",
    "vulnerability",
    "cve-",
    "breaking change",
    "breaking-change",
    "deprecat",
    "retirement",
    "retires",
    "end of life",
    "end-of-life",
    "enterprise policy",
    "critical fix",
    "critical update",
    "zero-day",
    "remote code execution",
    "privilege escalation",
    "data exfiltration",
]

# ── Never-post keywords ──────────────────────────────────────────────────────
# Items whose title *and* description contain ONLY these terms are suppressed.
# These are checked only when no always-post keyword matched.

NEVER_POST_PATTERNS: list[str] = [
    "emoji",
    "new theme",
    "color scheme",
    "icon update",
    "tooltip text",
    "typo fix",
    "spelling",
    "dark mode",
    "light mode",
    "ui polish",
    "minor bug fix",
    "minor performance",
    "quality of life",
    "cosmetic",
]


def evaluate(item: ChangeItem) -> RuleDecision:
    """Return a :class:`~src.models.RuleDecision` for the given item.

    The rule engine is intentionally conservative:
    - A single always-post keyword anywhere in the title/description is
      sufficient to force the item through.
    - A never-post decision requires that *none* of the always-post keywords
      are present, and that a never-post keyword appears in the title.
      Description matches alone are not enough (descriptions can be noisy).

    Returns
    -------
    RuleDecision
        ``ALWAYS_POST``, ``NEVER_POST``, or ``DEFER_TO_AI``.
    """
    combined = f"{item.title} {item.description}".lower()
    title_lower = item.title.lower()

    # Check always-post first (highest priority)
    for pattern in ALWAYS_POST_PATTERNS:
        if pattern in combined:
            return RuleDecision.ALWAYS_POST

    # Check never-post (title only, to reduce false negatives)
    for pattern in NEVER_POST_PATTERNS:
        if pattern in title_lower:
            return RuleDecision.NEVER_POST

    return RuleDecision.DEFER_TO_AI

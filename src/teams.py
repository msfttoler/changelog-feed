"""Microsoft Teams Workflows webhook poster.

Posts formatted CSA-friendly messages to a Teams channel via a
Power-Automate Workflows webhook (the modern replacement for legacy
Office 365 Incoming Webhooks).

Message format
--------------
The message deliberately does NOT dump AI output verbatim. Instead it
uses a deterministic template that AI inputs feed into, keeping the
channel signal-rich and readable.

Configuration
-------------
TEAMS_WEBHOOK_URL   Full HTTPS URL of the Teams Workflow trigger.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

import requests

from src.models import ClassificationResult, ScoredItem

logger = logging.getLogger(__name__)

# Source display names for the message header
_SOURCE_LABELS: dict[str, str] = {
    "github": "GitHub Platform",
    "vscode": "VS Code",
    "visualstudio": "Visual Studio",
}

# Relevance → emoji indicator
_RELEVANCE_EMOJI: dict[str, str] = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}

# Impact → readable label
_IMPACT_LABELS: dict[str, str] = {
    "none": "Minimal",
    "situational": "Situational – affects specific workloads",
    "broad": "Broad – affects most customers",
}


def _format_message(scored: ScoredItem) -> str:
    """Build a human-readable, CSA-friendly plain-text message."""
    item = scored.item
    clf: ClassificationResult | None = scored.classification

    source_label = _SOURCE_LABELS.get(item.source.value, item.source.value)
    area = item.product_area.value.title()
    relevance_emoji = (
        _RELEVANCE_EMOJI.get(clf.csa_relevance.value, "🔔") if clf else "🔔"
    )

    lines: list[str] = [
        f"{relevance_emoji} {source_label} Update – {area}",
        "",
        f"**What changed:**",
        f"• {item.title}",
        "",
    ]

    if item.description.strip():
        # Truncate long descriptions to keep messages scannable
        desc = item.description.strip()
        if len(desc) > 400:
            desc = desc[:397] + "..."
        lines += [f"**Details:**", f"{desc}", ""]

    if clf:
        lines += [
            "**Why this matters for CSAs:**",
            f"• {clf.why_it_matters}",
            "",
            "**Customer impact:**",
            f"• {_IMPACT_LABELS.get(clf.customer_impact.value, clf.customer_impact.value)}",
            "",
        ]
        if clf.categories:
            labels = " ".join(f"`{c}`" for c in clf.categories)
            lines += [f"**Tags:** {labels}", ""]

    rule_note = ""
    if scored.rule_decision.value == "always_post":
        rule_note = " *(rule: always post)*"

    lines.append(f"🔗 [Read more]({item.link}){rule_note}")

    return "\n".join(lines)


class TeamsWebhookPoster:
    """Posts formatted messages to a Teams channel via a Workflows webhook.

    The webhook URL is read from the ``TEAMS_WEBHOOK_URL`` environment
    variable by default, but can be overridden in the constructor.
    """

    def __init__(self, webhook_url: str | None = None, timeout: int = 10) -> None:
        self._webhook_url = webhook_url or os.environ.get("TEAMS_WEBHOOK_URL", "")
        self._timeout = timeout

        if not self._webhook_url:
            logger.warning(
                "TEAMS_WEBHOOK_URL is not set – Teams notifications will be skipped"
            )

    def post(self, scored: ScoredItem) -> bool:
        """Post a single scored item to Teams.

        Parameters
        ----------
        scored:
            A :class:`~src.models.ScoredItem` that has been marked for posting.

        Returns
        -------
        bool
            True on success, False on failure.
        """
        if not self._webhook_url:
            logger.warning("Skipping Teams post (no webhook URL configured)")
            return False

        message_text = _format_message(scored)

        # Teams Workflows webhook expects an Adaptive Card or simple text payload.
        # We use a text/markdown body for maximum compatibility.
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": message_text,
                                "wrap": True,
                                "markdown": True,
                            }
                        ],
                    },
                }
            ],
        }

        try:
            resp = requests.post(
                self._webhook_url,
                json=payload,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code in (200, 202):
                logger.info(
                    "Posted to Teams: %s [%s]",
                    scored.item.title,
                    resp.status_code,
                )
                return True
            else:
                logger.error(
                    "Teams webhook returned %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return False
        except Exception:
            logger.exception("Failed to post to Teams for item: %s", scored.item.title)
            return False

    def post_batch(self, items: list[ScoredItem]) -> int:
        """Post multiple scored items; returns count of successful posts."""
        return sum(1 for item in items if self.post(item))

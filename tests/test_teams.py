"""Tests for the Teams webhook poster."""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
import responses as resp_lib

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
from src.teams import TeamsWebhookPoster, _format_message

WEBHOOK_URL = "https://prod-123.westus.logic.azure.com/workflows/test"


def make_scored_item(
    title: str = "Security fix for auth",
    source: Source = Source.GITHUB,
    product_area: ProductArea = ProductArea.SECURITY,
    rule_decision: RuleDecision = RuleDecision.ALWAYS_POST,
    should_post: bool = True,
) -> ScoredItem:
    item = ChangeItem(
        id="teams_test",
        source=source,
        product_area=product_area,
        title=title,
        description="Full description of the change.",
        link="https://example.com/changelog/1",
        published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        raw_text="raw text",
    )
    clf = ClassificationResult(
        csa_relevance=CSARelevance.HIGH,
        why_it_matters="Impacts enterprise security posture",
        customer_impact=CustomerImpact.BROAD,
        conversation_trigger=True,
        categories=["security", "breaking-change"],
        confidence=0.95,
    )
    return ScoredItem(
        item=item,
        rule_decision=rule_decision,
        classification=clf,
        should_post=should_post,
    )


class TestFormatMessage:
    def test_includes_title(self):
        scored = make_scored_item(title="Critical vulnerability patch")
        msg = _format_message(scored)
        assert "Critical vulnerability patch" in msg

    def test_includes_source_label(self):
        scored = make_scored_item(source=Source.GITHUB)
        msg = _format_message(scored)
        assert "GitHub Platform" in msg

    def test_includes_why_it_matters(self):
        scored = make_scored_item()
        msg = _format_message(scored)
        assert "enterprise security posture" in msg

    def test_includes_customer_impact(self):
        scored = make_scored_item()
        msg = _format_message(scored)
        assert "Broad" in msg

    def test_includes_link(self):
        scored = make_scored_item()
        msg = _format_message(scored)
        assert "https://example.com/changelog/1" in msg

    def test_always_post_rule_note(self):
        scored = make_scored_item(rule_decision=RuleDecision.ALWAYS_POST)
        msg = _format_message(scored)
        assert "rule: always post" in msg

    def test_no_classification_still_formats(self):
        item = ChangeItem(
            id="x",
            source=Source.VSCODE,
            product_area=ProductArea.IDE,
            title="VS Code update",
            description="Something happened",
            link="https://code.visualstudio.com",
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            raw_text="raw",
        )
        scored = ScoredItem(item=item, rule_decision=RuleDecision.ALWAYS_POST, should_post=True)
        msg = _format_message(scored)
        assert "VS Code" in msg

    def test_vscode_source_label(self):
        scored = make_scored_item(source=Source.VSCODE)
        msg = _format_message(scored)
        assert "VS Code" in msg

    def test_visualstudio_source_label(self):
        scored = make_scored_item(source=Source.VISUALSTUDIO)
        msg = _format_message(scored)
        assert "Visual Studio" in msg


class TestTeamsWebhookPoster:
    def test_no_webhook_url_returns_false(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("TEAMS_WEBHOOK_URL", None)
            poster = TeamsWebhookPoster(webhook_url=None)
            scored = make_scored_item()
            assert poster.post(scored) is False

    @resp_lib.activate
    def test_successful_post_returns_true(self):
        resp_lib.add(
            resp_lib.POST,
            WEBHOOK_URL,
            json={"status": "ok"},
            status=200,
        )
        poster = TeamsWebhookPoster(webhook_url=WEBHOOK_URL)
        scored = make_scored_item()
        result = poster.post(scored)
        assert result is True
        assert len(resp_lib.calls) == 1

    @resp_lib.activate
    def test_failed_post_returns_false(self):
        resp_lib.add(
            resp_lib.POST,
            WEBHOOK_URL,
            json={"error": "bad request"},
            status=400,
        )
        poster = TeamsWebhookPoster(webhook_url=WEBHOOK_URL)
        scored = make_scored_item()
        result = poster.post(scored)
        assert result is False

    @resp_lib.activate
    def test_post_batch_returns_count(self):
        resp_lib.add(resp_lib.POST, WEBHOOK_URL, json={}, status=200)
        resp_lib.add(resp_lib.POST, WEBHOOK_URL, json={}, status=200)
        poster = TeamsWebhookPoster(webhook_url=WEBHOOK_URL)
        items = [make_scored_item(), make_scored_item()]
        count = poster.post_batch(items)
        assert count == 2

    @resp_lib.activate
    def test_post_sends_adaptive_card_payload(self):
        resp_lib.add(resp_lib.POST, WEBHOOK_URL, json={}, status=200)
        poster = TeamsWebhookPoster(webhook_url=WEBHOOK_URL)
        scored = make_scored_item()
        poster.post(scored)

        request_body = resp_lib.calls[0].request.body
        import json
        payload = json.loads(request_body)
        # Verify it's an AdaptiveCard message
        assert payload["type"] == "message"
        assert payload["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"

    def test_network_error_returns_false(self):
        import requests
        poster = TeamsWebhookPoster(webhook_url=WEBHOOK_URL)
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("down")):
            result = poster.post(make_scored_item())
        assert result is False

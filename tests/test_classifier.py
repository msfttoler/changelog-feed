"""Tests for the AI classifier module."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.models import (
    ChangeItem,
    ClassificationResult,
    CSARelevance,
    CustomerImpact,
    ProductArea,
    Source,
)
from src.classifier import _parse_response, AIClassifier


def make_item(**kwargs) -> ChangeItem:
    defaults = dict(
        id="clf_test",
        source=Source.GITHUB,
        product_area=ProductArea.COPILOT,
        title="Copilot now supports multi-file edits",
        description="GitHub Copilot can now suggest edits across multiple files.",
        link="https://github.blog/changelog/1",
        published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        raw_text="Full text here",
    )
    defaults.update(kwargs)
    return ChangeItem(**defaults)


SAMPLE_RESPONSE_JSON = json.dumps({
    "csa_relevance": "high",
    "why_it_matters": "Impacts enterprise Copilot adoption discussions",
    "customer_impact": "broad",
    "conversation_trigger": True,
    "categories": ["copilot", "enterprise"],
    "confidence": 0.92,
})


class TestParseResponse:
    def test_parses_valid_json(self):
        result = _parse_response(SAMPLE_RESPONSE_JSON)
        assert isinstance(result, ClassificationResult)
        assert result.csa_relevance == CSARelevance.HIGH
        assert result.customer_impact == CustomerImpact.BROAD
        assert result.conversation_trigger is True
        assert result.confidence == 0.92
        assert "copilot" in result.categories

    def test_strips_markdown_code_fences(self):
        fenced = f"```json\n{SAMPLE_RESPONSE_JSON}\n```"
        result = _parse_response(fenced)
        assert result.csa_relevance == CSARelevance.HIGH

    def test_defaults_on_missing_fields(self):
        minimal = json.dumps({
            "csa_relevance": "medium",
            "why_it_matters": "Some reason",
            "customer_impact": "situational",
            "conversation_trigger": False,
            "categories": [],
            "confidence": 0.5,
        })
        result = _parse_response(minimal)
        assert result.csa_relevance == CSARelevance.MEDIUM


class TestAIClassifier:
    def _make_mock_client(self, json_content: str):
        """Build a mock openai client that returns json_content."""
        mock_message = MagicMock()
        mock_message.content = json_content
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    def test_classify_returns_result(self):
        mock_client = self._make_mock_client(SAMPLE_RESPONSE_JSON)
        classifier = AIClassifier.__new__(AIClassifier)
        classifier._client = mock_client
        classifier._model = "gpt-4o"

        item = make_item()
        result = classifier.classify(item)

        assert result.csa_relevance == CSARelevance.HIGH
        assert result.confidence == 0.92
        mock_client.chat.completions.create.assert_called_once()

    def test_classify_batch_returns_all_results(self):
        mock_client = self._make_mock_client(SAMPLE_RESPONSE_JSON)
        classifier = AIClassifier.__new__(AIClassifier)
        classifier._client = mock_client
        classifier._model = "gpt-4o"

        items = [make_item(id=f"item_{i}") for i in range(3)]
        results = classifier.classify_batch(items)

        assert len(results) == 3
        assert all(r.csa_relevance == CSARelevance.HIGH for r in results)

    def test_classify_batch_fallback_on_error(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API error")
        classifier = AIClassifier.__new__(AIClassifier)
        classifier._client = mock_client
        classifier._model = "gpt-4o"

        items = [make_item()]
        results = classifier.classify_batch(items)

        assert len(results) == 1
        assert results[0].csa_relevance == CSARelevance.LOW
        assert results[0].confidence == 0.0

    def test_build_classifier_raises_without_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            # Remove all credential env vars
            import os
            for key in ("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"):
                os.environ.pop(key, None)

            from src.classifier import _build_client
            with pytest.raises(RuntimeError, match="No AI credentials"):
                _build_client()

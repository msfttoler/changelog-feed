"""AI classifier for CSA relevance scoring.

Uses OpenAI (or Azure OpenAI) to classify each :class:`~src.models.ChangeItem`
against a CSA-focused rubric, producing a structured
:class:`~src.models.ClassificationResult`.

AI's role here is *bounded*: it supplies scoring and explanation but does NOT
decide whether to post. That decision belongs to the PostDecisionEngine.

Configuration (via environment variables):
    OPENAI_API_KEY          – OpenAI API key (standard OpenAI).
    AZURE_OPENAI_API_KEY    – Azure OpenAI API key.
    AZURE_OPENAI_ENDPOINT   – Azure OpenAI endpoint URL.
    AZURE_OPENAI_DEPLOYMENT – Azure OpenAI deployment name.
    OPENAI_MODEL            – Model name for standard OpenAI (default: gpt-4o).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from src.models import ChangeItem, ClassificationResult, CSARelevance, CustomerImpact

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are evaluating product changes from GitHub, Visual Studio, and VS Code
for a Cloud Solution Architect (CSA) audience at Microsoft.

Prioritise changes that impact:
- Customer architectures and design decisions
- Security posture and compliance
- Developer velocity and toolchain choices
- Enterprise governance and manageability
- Breaking changes or deprecations that customers need to act on

Deprioritise:
- UI polish and cosmetic updates
- Minor bug fixes with no architectural impact
- End-user convenience features that do not affect scale or security
- Emoji packs, themes, and icon changes

Return ONLY a JSON object with exactly these fields:
{
  "csa_relevance": "high" | "medium" | "low",
  "why_it_matters": "<one sentence for a CSA>",
  "customer_impact": "none" | "situational" | "broad",
  "conversation_trigger": true | false,
  "categories": ["<label>", ...],
  "confidence": <float 0.0-1.0>
}

Do not include any explanation or markdown outside the JSON object."""

_USER_PROMPT_TEMPLATE = """Source: {source}
Product area: {product_area}
Title: {title}
Description: {description}
Raw category: {raw_category}"""


def _build_client() -> tuple[Any, str]:
    """Build an OpenAI-compatible client and return (client, model_or_deployment).

    Prefers Azure OpenAI when the Azure env vars are present.
    Falls back to standard OpenAI.

    Raises
    ------
    RuntimeError
        If neither Azure nor OpenAI credentials are configured.
    """
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

    if azure_key and azure_endpoint and azure_deployment:
        try:
            from openai import AzureOpenAI  # type: ignore[attr-defined]

            client = AzureOpenAI(
                api_key=azure_key,
                azure_endpoint=azure_endpoint,
                api_version="2024-02-01",
            )
            return client, azure_deployment
        except ImportError:
            pass

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        from openai import OpenAI

        model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        client = OpenAI(api_key=openai_key)
        return client, model

    raise RuntimeError(
        "No AI credentials configured. "
        "Set OPENAI_API_KEY or the three AZURE_OPENAI_* environment variables."
    )


def _parse_response(content: str) -> ClassificationResult:
    """Parse the raw JSON string returned by the model."""
    # Strip markdown code fences if the model added them
    text = content.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
        text = text.rstrip("`").strip()

    data = json.loads(text)

    return ClassificationResult(
        csa_relevance=CSARelevance(data.get("csa_relevance", "low")),
        why_it_matters=data.get("why_it_matters", ""),
        customer_impact=CustomerImpact(data.get("customer_impact", "none")),
        conversation_trigger=bool(data.get("conversation_trigger", False)),
        categories=data.get("categories", []),
        confidence=float(data.get("confidence", 0.5)),
    )


class AIClassifier:
    """Classifies change items using an LLM with a CSA-specific rubric."""

    def __init__(self) -> None:
        self._client, self._model = _build_client()

    def classify(self, item: ChangeItem) -> ClassificationResult:
        """Return a classification for a single :class:`~src.models.ChangeItem`.

        Parameters
        ----------
        item:
            The normalized change item to classify.

        Returns
        -------
        ClassificationResult
            Structured classification output from the AI model.
        """
        user_message = _USER_PROMPT_TEMPLATE.format(
            source=item.source.value,
            product_area=item.product_area.value,
            title=item.title,
            description=item.description[:1500],
            raw_category=item.raw_category or "none",
        )

        logger.debug("Classifying item: %s", item.title)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
            max_tokens=400,
        )

        raw = response.choices[0].message.content or ""
        result = _parse_response(raw)
        logger.debug("Classification result for '%s': %s", item.title, result.csa_relevance)
        return result

    def classify_batch(self, items: list[ChangeItem]) -> list[ClassificationResult]:
        """Classify a list of items, returning results in the same order.

        Items that fail to classify receive a fallback LOW result.
        """
        results: list[ClassificationResult] = []
        for item in items:
            try:
                results.append(self.classify(item))
            except Exception:
                logger.exception("Classification failed for item '%s'; using fallback", item.title)
                results.append(
                    ClassificationResult(
                        csa_relevance=CSARelevance.LOW,
                        why_it_matters="Classification unavailable",
                        customer_impact=CustomerImpact.NONE,
                        conversation_trigger=False,
                        categories=[],
                        confidence=0.0,
                    )
                )
        return results

"""AI-powered summarization for top changelog entries.

Uses OpenAI when OPENAI_API_KEY is set; otherwise falls back to
heuristic keyword-based summaries.
"""

from __future__ import annotations

import json
import logging
import os

from .models import ChangeEntry

logger = logging.getLogger(__name__)

# Number of top entries to generate highlights for
_MAX_HIGHLIGHTS = 8

# ---------------------------------------------------------------------------
# Keyword-to-impact mapping for the heuristic fallback
# ---------------------------------------------------------------------------

_IMPACT_RULES: list[tuple[list[str], str]] = [
    (
        ["security", "vulnerability", "cve-", "zero-day", "exploit", "advisory",
         "injection", "xss", "privilege escalation", "remote code execution"],
        "Security advisory — review immediately for potential exposure.",
    ),
    (
        ["breaking change", "breaking-change", "deprecat", "removal",
         "end of life", "end-of-life", "retirement", "sunset", "discontinued"],
        "Breaking change — may require code or workflow updates.",
    ),
    (
        ["copilot", "github copilot", "ai assist", "ai completion",
         "ai code", "ai chat", "agent mode"],
        "AI/Copilot update — new capabilities for AI-assisted development.",
    ),
    (
        ["general availability", "ga release", "now available", "launch",
         "announcing", "introducing"],
        "New general-availability feature — ready for production use.",
    ),
    (
        ["preview", "beta", "experimental", "insider"],
        "Preview/beta feature — available for early testing.",
    ),
    (
        ["performance", "faster", "speed", "latency", "throughput"],
        "Performance improvement — faster workflows ahead.",
    ),
    (
        ["bug fix", "bugfix", "patch", "hotfix", "resolved"],
        "Bug fix — addresses a known issue.",
    ),
]


def _heuristic_summary(entry: ChangeEntry) -> str:
    """Generate a short impact summary from keyword matching."""
    text = (entry.title + " " + entry.description + " " + " ".join(entry.tags)).lower()
    for keywords, summary in _IMPACT_RULES:
        if any(kw in text for kw in keywords):
            return summary
    return "Notable update — see the full changelog for details."


# ---------------------------------------------------------------------------
# OpenAI-powered summarizer
# ---------------------------------------------------------------------------

def _openai_summarize(entries: list[ChangeEntry]) -> dict[str, str]:
    """Call OpenAI to generate 'why this matters' blurbs. Returns {entry_id: summary}."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed; falling back to heuristic")
        return {}

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {}

    client = OpenAI(api_key=api_key)

    items = []
    for e in entries:
        items.append({
            "id": e.id,
            "source": e.source,
            "title": e.title,
            "description": e.description[:300],
        })

    prompt = (
        "You are a developer-tools analyst. For each changelog entry below, "
        "write a one-sentence 'Why this matters' summary (max 120 chars) "
        "explaining the practical impact for developers.\n\n"
        "Return ONLY a JSON object mapping each entry id to its summary string.\n\n"
        "Entries:\n" + json.dumps(items, indent=2)
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception:
        logger.exception("OpenAI summarization failed; falling back to heuristic")
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_summaries(entries: list[ChangeEntry]) -> list[ChangeEntry]:
    """Mark top entries as highlights and add AI/heuristic summaries.

    Entries should already be scored and sorted (highest score first).
    Returns a new list with `highlight` and `ai_summary` fields set.
    """
    top = entries[:_MAX_HIGHLIGHTS]

    # Try OpenAI first
    ai_map = _openai_summarize(top)
    if ai_map:
        logger.info("Generated %d AI summaries via OpenAI", len(ai_map))

    result: list[ChangeEntry] = []
    top_ids = {e.id for e in top}

    for entry in entries:
        updates: dict = {}
        if entry.id in top_ids:
            updates["highlight"] = True
            summary = ai_map.get(entry.id, "")
            if not summary:
                summary = _heuristic_summary(entry)
            updates["ai_summary"] = summary
        result.append(entry.model_copy(update=updates))

    return result

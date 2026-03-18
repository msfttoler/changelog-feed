"""Heuristic importance scoring for changelog entries."""

from __future__ import annotations

from .models import ChangeEntry

_WEIGHTS: list[tuple[set[str], int]] = [
    (
        {
            "security", "vulnerability", "cve-", "zero-day", "exploit",
            "advisory", "authentication bypass", "injection", "xss",
            "privilege escalation", "remote code execution",
        },
        40,
    ),
    (
        {
            "breaking change", "breaking-change", "deprecat", "removal",
            "end of life", "end-of-life", "retirement", "sunset",
            "discontinued", "removed",
        },
        35,
    ),
    ({"copilot", "github copilot", "ai assist", "ai completion"}, 15),
    (
        {
            "introducing", "now available", "general availability",
            "ga release", "new feature", "announcing", "launch", "preview",
        },
        10,
    ),
    ({"performance", "faster", "speed", "latency", "throughput"}, 5),
    ({"bug fix", "bugfix", "patch", "hotfix", "resolved"}, 3),
]


def score_entry(entry: ChangeEntry) -> ChangeEntry:
    """Return a copy of *entry* with score and severity set."""
    text = (entry.title + " " + entry.description + " " + " ".join(entry.tags)).lower()

    s = 10  # base
    for keywords, weight in _WEIGHTS:
        if any(kw in text for kw in keywords):
            s += weight
    s = min(s, 100)

    if s >= 75:
        severity = "critical"
    elif s >= 50:
        severity = "high"
    elif s >= 25:
        severity = "medium"
    else:
        severity = "low"

    return entry.model_copy(update={"score": s, "severity": severity})

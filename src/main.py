"""Main orchestrator for the changelog-feed signal engine.

Reference architecture (from the PRD):

    [Scheduler / Webhook]
            ↓
    [Feed Ingestion]           ← ingestors/
            ↓
    [Normalizer + Dedupe]      ← state.py (SQLite)
            ↓
    [Rule Engine]              ← rule_engine.py
            ↓
    [AI Classifier]            ← classifier.py
            ↓
    [Post Decision Engine]     ← post_engine.py
            ↓
    [Teams Workflow Webhook]   ← teams.py

Usage
-----
Run directly::

    python -m src.main

Or call ``run_pipeline()`` from another entry-point (Azure Function,
Logic App HTTP trigger, etc.).

Environment variables (see ``.env.example`` for the full list):
    OPENAI_API_KEY / AZURE_OPENAI_* – AI credentials
    TEAMS_WEBHOOK_URL               – Teams Workflows webhook
    MIN_RELEVANCE                   – Minimum CSA relevance to post
    STATE_DB_PATH                   – SQLite state file location
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from src.ingestors.github_changelog import GitHubChangelogIngestor
from src.ingestors.visual_studio import VisualStudioIngestor
from src.ingestors.vscode import VSCodeIngestor
from src.models import ChangeItem, ScoredItem
from src.post_engine import PostDecisionEngine
from src.state import StateStore
from src.teams import TeamsWebhookPoster

if TYPE_CHECKING:
    from src.classifier import AIClassifier

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _build_classifier() -> "AIClassifier | None":
    """Try to build an AI classifier; return None if credentials are missing."""
    has_azure = all(
        os.environ.get(v)
        for v in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")
    )
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))

    if not has_azure and not has_openai:
        logger.warning(
            "No AI credentials found – running in rule-only mode. "
            "Set OPENAI_API_KEY or AZURE_OPENAI_* to enable AI classification."
        )
        return None

    from src.classifier import AIClassifier

    return AIClassifier()


def run_pipeline(
    dry_run: bool = False,
    db_path: str | None = None,
) -> dict[str, int]:
    """Run the full ingestion → classification → posting pipeline.

    Parameters
    ----------
    dry_run:
        When True, log what *would* be posted but do not call the Teams
        webhook or update the state store.  Useful for testing.
    db_path:
        Path to the SQLite state database.  Defaults to the value of the
        ``STATE_DB_PATH`` env var, or ``.changelog_feed_state.db``.

    Returns
    -------
    dict[str, int]
        Summary statistics: ``ingested``, ``new``, ``posted``.
    """
    state_path = db_path or os.environ.get("STATE_DB_PATH", ".changelog_feed_state.db")

    # ── 1. Ingest ────────────────────────────────────────────────────────────
    ingestors = [
        GitHubChangelogIngestor(),
        VSCodeIngestor(),
        VisualStudioIngestor(),
    ]

    all_items: list[ChangeItem] = []
    for ingestor in ingestors:
        try:
            all_items.extend(ingestor.fetch_items())
        except Exception:
            logger.exception("Ingestor %s failed", type(ingestor).__name__)

    logger.info("Ingested %d items total", len(all_items))

    # ── 2. Deduplicate ───────────────────────────────────────────────────────
    with StateStore(state_path) as store:
        new_items = [
            item
            for item in all_items
            if not store.is_seen(item.source.value, item.id)
        ]
        logger.info("%d new items (after deduplication)", len(new_items))

        if not new_items:
            return {"ingested": len(all_items), "new": 0, "posted": 0}

        # ── 3. Classify + decide ─────────────────────────────────────────────
        classifier = _build_classifier()
        engine = PostDecisionEngine(classifier=classifier)
        scored_items: list[ScoredItem] = engine.evaluate_batch(new_items)

        to_post = [s for s in scored_items if s.should_post]
        logger.info(
            "%d items marked for posting (rule_only=%s)",
            len(to_post),
            classifier is None,
        )

        # ── 4. Post ──────────────────────────────────────────────────────────
        posted_count = 0
        if dry_run:
            for s in to_post:
                logger.info(
                    "[DRY RUN] Would post: [%s] %s",
                    s.rule_decision.value,
                    s.item.title,
                )
            posted_count = len(to_post)
        else:
            poster = TeamsWebhookPoster()
            posted_count = poster.post_batch(to_post)

        # ── 5. Mark seen ─────────────────────────────────────────────────────
        if not dry_run:
            store.mark_seen_batch(
                [(item.source.value, item.id) for item in new_items]
            )
            logger.info("Marked %d items as seen", len(new_items))

    return {
        "ingested": len(all_items),
        "new": len(new_items),
        "posted": posted_count,
    }


def main() -> None:
    """CLI entry-point."""
    _configure_logging()
    load_dotenv()

    import argparse

    parser = argparse.ArgumentParser(
        description="changelog-feed: CSA signal engine for GitHub, VS Code, and Visual Studio"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ingest and classify but do not post to Teams or update state",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to the SQLite state database (default: .changelog_feed_state.db)",
    )
    args = parser.parse_args()

    result = run_pipeline(dry_run=args.dry_run, db_path=args.db_path)
    logger.info(
        "Pipeline complete – ingested=%d  new=%d  posted=%d",
        result["ingested"],
        result["new"],
        result["posted"],
    )


if __name__ == "__main__":
    main()

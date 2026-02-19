"""GitHub changelog ingestor.

Ingests items from the GitHub platform changelog RSS feed at
https://github.blog/changelog/feed/

Each RSS entry maps directly to one :class:`~src.models.ChangeItem`.
The category tags present in the feed are used to determine the
:class:`~src.models.ProductArea`.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from src.ingestors.base import BaseIngestor
from src.models import ChangeItem, ProductArea, Source

logger = logging.getLogger(__name__)

CHANGELOG_RSS_URL = "https://github.blog/changelog/feed/"

# Map RSS category tags → ProductArea
_CATEGORY_MAP: dict[str, ProductArea] = {
    "copilot": ProductArea.COPILOT,
    "github copilot": ProductArea.COPILOT,
    "actions": ProductArea.ACTIONS,
    "github actions": ProductArea.ACTIONS,
    "security": ProductArea.SECURITY,
    "secret scanning": ProductArea.SECURITY,
    "code scanning": ProductArea.SECURITY,
    "dependabot": ProductArea.SECURITY,
    "enterprise": ProductArea.ENTERPRISE,
    "admin": ProductArea.ENTERPRISE,
    "codespaces": ProductArea.DEVCONTAINERS,
    "dev containers": ProductArea.DEVCONTAINERS,
}


def _infer_product_area(tags: list[str]) -> ProductArea:
    """Return the best-matching ProductArea from a list of category tags."""
    for tag in tags:
        normalized = tag.lower().strip()
        if normalized in _CATEGORY_MAP:
            return _CATEGORY_MAP[normalized]
        # Partial-match fallback
        for key, area in _CATEGORY_MAP.items():
            if key in normalized or normalized in key:
                return area
    return ProductArea.OTHER


def _parse_published(entry: feedparser.FeedParserDict) -> datetime:
    """Parse a feedparser entry's published date into an aware datetime."""
    if hasattr(entry, "published") and entry.published:
        try:
            return parsedate_to_datetime(entry.published).astimezone(timezone.utc)
        except Exception:
            pass
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc)


def _stable_id(link: str) -> str:
    """Return a stable 12-char hex ID derived from the item URL."""
    return hashlib.sha1(link.encode()).hexdigest()[:12]


class GitHubChangelogIngestor(BaseIngestor):
    """Ingests the GitHub platform changelog RSS feed."""

    def __init__(self, feed_url: str = CHANGELOG_RSS_URL) -> None:
        self._feed_url = feed_url

    def fetch_items(self) -> list[ChangeItem]:
        logger.info("Fetching GitHub changelog from %s", self._feed_url)
        feed = feedparser.parse(self._feed_url)

        if feed.bozo and not feed.entries:
            logger.warning("GitHub changelog feed parse error: %s", feed.bozo_exception)
            return []

        items: list[ChangeItem] = []
        for entry in feed.entries:
            try:
                items.append(self._normalize(entry))
            except Exception:
                logger.exception("Failed to normalize GitHub changelog entry: %s", entry)

        logger.info("GitHub changelog: fetched %d items", len(items))
        return items

    def _normalize(self, entry: feedparser.FeedParserDict) -> ChangeItem:
        link: str = entry.get("link", "")
        tags: list[str] = [t.get("term", "") for t in entry.get("tags", [])]
        raw_text: str = entry.get("summary", entry.get("title", ""))

        # Strip HTML tags from summary for a clean description
        try:
            from bs4 import BeautifulSoup

            description = BeautifulSoup(raw_text, "lxml").get_text(" ", strip=True)
        except Exception:
            description = raw_text

        return ChangeItem(
            id=_stable_id(link),
            source=Source.GITHUB,
            product_area=_infer_product_area(tags),
            title=entry.get("title", ""),
            description=description[:2000],
            link=link,
            published_at=_parse_published(entry),
            raw_category=", ".join(tags) if tags else None,
            raw_text=raw_text[:4000],
        )

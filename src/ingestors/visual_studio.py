"""Visual Studio release notes ingestor.

Visual Studio publishes detailed release notes on Microsoft Learn at
https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-notes

This ingestor:
1. Fetches the latest GA and Preview release notes pages.
2. Parses the HTML into individual change sections.
3. Normalizes each section into a :class:`~src.models.ChangeItem`.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup, Tag

from src.ingestors.base import BaseIngestor
from src.models import ChangeItem, ProductArea, Source

logger = logging.getLogger(__name__)

# Visual Studio 2022 GA release notes
VS_RELEASE_NOTES_URLS: list[str] = [
    "https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-notes",
    "https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-notes-preview",
]

_SECTION_MAP: list[tuple[str, ProductArea]] = [
    ("security", ProductArea.SECURITY),
    ("vulnerabilit", ProductArea.SECURITY),
    ("cve", ProductArea.SECURITY),
    ("github copilot", ProductArea.COPILOT),
    ("copilot", ProductArea.COPILOT),
    ("enterprise", ProductArea.ENTERPRISE),
    ("group policy", ProductArea.ENTERPRISE),
    ("remote", ProductArea.DEVCONTAINERS),
    ("container", ProductArea.DEVCONTAINERS),
    ("breaking", ProductArea.IDE),
    ("deprecat", ProductArea.IDE),
    ("debug", ProductArea.IDE),
    ("test", ProductArea.IDE),
]


def _infer_product_area(text: str) -> ProductArea:
    lower = text.lower()
    for keyword, area in _SECTION_MAP:
        if keyword in lower:
            return area
    return ProductArea.IDE


def _stable_id(url: str, heading: str) -> str:
    key = f"{url}#{heading}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


class VisualStudioIngestor(BaseIngestor):
    """Ingests Visual Studio release notes from Microsoft Learn."""

    def __init__(
        self,
        release_urls: list[str] | None = None,
        timeout: int = 15,
    ) -> None:
        self._release_urls = release_urls or VS_RELEASE_NOTES_URLS
        self._timeout = timeout

    def fetch_items(self) -> list[ChangeItem]:
        items: list[ChangeItem] = []
        for url in self._release_urls:
            items.extend(self._fetch_one(url))
        logger.info("Visual Studio: fetched %d items total", len(items))
        return items

    def _fetch_one(self, url: str) -> list[ChangeItem]:
        logger.info("Fetching Visual Studio release notes from %s", url)
        try:
            resp = requests.get(url, timeout=self._timeout)
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to fetch Visual Studio release notes from %s", url)
            return []
        return self._parse_page(resp.text, url)

    def _parse_page(self, html: str, url: str) -> list[ChangeItem]:
        """Parse individual change sections from a Visual Studio release notes page."""
        soup = BeautifulSoup(html, "lxml")

        published_at = self._extract_date(soup) or datetime.now(tz=timezone.utc)

        # Find the latest version heading (H2 starting with a version number)
        items: list[ChangeItem] = []
        version_heading: str = "Unknown"

        for tag in soup.find_all(["h2", "h3"]):
            heading_text = tag.get_text(" ", strip=True)

            # Track the current version context from H2 headings
            if tag.name == "h2" and re.match(r"\d+\.\d+", heading_text):
                version_heading = heading_text
                continue

            if not heading_text or len(heading_text) < 4:
                continue

            # Collect content for this section
            body_parts: list[str] = []
            for sibling in tag.find_next_siblings():
                if isinstance(sibling, Tag) and sibling.name in ("h2", "h3"):
                    break
                text = sibling.get_text(" ", strip=True)
                if text:
                    body_parts.append(text)
                if len(body_parts) >= 5:
                    break

            if not body_parts:
                continue

            raw_text = f"{version_heading} – {heading_text}\n\n" + "\n".join(body_parts)
            description = "\n".join(body_parts)[:2000]

            items.append(
                ChangeItem(
                    id=_stable_id(url, f"{version_heading}#{heading_text}"),
                    source=Source.VISUALSTUDIO,
                    product_area=_infer_product_area(heading_text + " " + description),
                    title=f"Visual Studio {version_heading}: {heading_text}",
                    description=description,
                    link=url,
                    published_at=published_at,
                    raw_category=heading_text,
                    raw_text=raw_text[:4000],
                )
            )

            # Limit to first 30 sections (most recent version)
            if len(items) >= 30:
                break

        logger.info("Visual Studio: parsed %d sections from %s", len(items), url)
        return items

    def _extract_date(self, soup: BeautifulSoup) -> datetime | None:
        """Try to extract publish date from page meta tags."""
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            try:
                return datetime.fromisoformat(meta["content"]).astimezone(timezone.utc)
            except Exception:
                pass
        return None

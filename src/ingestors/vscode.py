"""VS Code release notes ingestor.

VS Code ships monthly releases with detailed release notes pages at
https://code.visualstudio.com/updates/v<major>_<minor>

This ingestor:
1. Fetches the latest release notes page URL from the VS Code updates index.
2. Parses the HTML into individual H2 section items (one per section heading).
3. Normalizes each section into a :class:`~src.models.ChangeItem`.

Each section heading (e.g. "Remote Development", "Notebooks", "Extension authoring")
becomes a separate, independently scorable item.
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

VSCODE_UPDATES_URL = "https://code.visualstudio.com/updates/"

# Map section headings → ProductArea
_SECTION_MAP: list[tuple[str, ProductArea]] = [
    ("remote", ProductArea.DEVCONTAINERS),
    ("container", ProductArea.DEVCONTAINERS),
    ("wsl", ProductArea.DEVCONTAINERS),
    ("codespace", ProductArea.DEVCONTAINERS),
    ("dev container", ProductArea.DEVCONTAINERS),
    ("copilot", ProductArea.COPILOT),
    ("github copilot", ProductArea.COPILOT),
    ("security", ProductArea.SECURITY),
    ("authentication", ProductArea.SECURITY),
    ("enterprise", ProductArea.ENTERPRISE),
    ("policy", ProductArea.ENTERPRISE),
    ("extension author", ProductArea.IDE),
    ("extension api", ProductArea.IDE),
    ("language", ProductArea.IDE),
    ("debug", ProductArea.IDE),
    ("notebook", ProductArea.IDE),
    ("editor", ProductArea.IDE),
]


def _infer_product_area(heading: str) -> ProductArea:
    lower = heading.lower()
    for keyword, area in _SECTION_MAP:
        if keyword in lower:
            return area
    return ProductArea.IDE


def _stable_id(link: str, heading: str) -> str:
    key = f"{link}#{heading}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def _extract_version_from_url(url: str) -> str:
    """Extract the version string from a VS Code updates URL, e.g. 'v1_97'."""
    m = re.search(r"/(v\d+_\d+)", url)
    return m.group(1) if m else "unknown"


class VSCodeIngestor(BaseIngestor):
    """Ingests the latest VS Code monthly release notes."""

    def __init__(
        self,
        updates_url: str = VSCODE_UPDATES_URL,
        timeout: int = 15,
    ) -> None:
        self._updates_url = updates_url
        self._timeout = timeout

    def fetch_items(self) -> list[ChangeItem]:
        logger.info("Fetching VS Code release notes index from %s", self._updates_url)
        try:
            resp = requests.get(self._updates_url, timeout=self._timeout)
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to fetch VS Code updates index")
            return []

        release_url = self._find_latest_release_url(resp.text, self._updates_url)
        if not release_url:
            logger.warning("Could not determine latest VS Code release URL")
            return []

        return self._fetch_release_page(release_url)

    def _find_latest_release_url(self, html: str, base_url: str) -> str | None:
        """Find the href of the most-recent monthly release from the index page."""
        soup = BeautifulSoup(html, "lxml")
        # The index page lists releases as links matching /updates/v<major>_<minor>
        for a in soup.find_all("a", href=re.compile(r"/updates/v\d+_\d+")):
            href = a["href"]
            if href.startswith("/"):
                href = "https://code.visualstudio.com" + href
            return href  # first match is the latest
        return None

    def _fetch_release_page(self, url: str) -> list[ChangeItem]:
        logger.info("Fetching VS Code release notes from %s", url)
        try:
            resp = requests.get(url, timeout=self._timeout)
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to fetch VS Code release page %s", url)
            return []

        version = _extract_version_from_url(url)
        return self._parse_release_page(resp.text, url, version)

    def _parse_release_page(self, html: str, url: str, version: str) -> list[ChangeItem]:
        """Parse individual H2 sections from a VS Code release notes page."""
        soup = BeautifulSoup(html, "lxml")

        # Extract approximate publish date from the page or use today
        published_at = self._extract_date(soup) or datetime.now(tz=timezone.utc)

        items: list[ChangeItem] = []
        for h2 in soup.find_all("h2"):
            heading_text = h2.get_text(" ", strip=True)
            if not heading_text or heading_text.lower() in ("thank you", "notable fixes"):
                continue

            # Collect paragraphs/list-items until the next H2
            body_parts: list[str] = []
            for sibling in h2.find_next_siblings():
                if isinstance(sibling, Tag) and sibling.name == "h2":
                    break
                text = sibling.get_text(" ", strip=True)
                if text:
                    body_parts.append(text)
                if len(body_parts) >= 5:
                    break

            raw_text = f"{heading_text}\n\n" + "\n".join(body_parts)
            description = "\n".join(body_parts)[:2000] or heading_text

            items.append(
                ChangeItem(
                    id=_stable_id(url, heading_text),
                    source=Source.VSCODE,
                    product_area=_infer_product_area(heading_text),
                    title=f"VS Code {version}: {heading_text}",
                    description=description,
                    link=url,
                    published_at=published_at,
                    raw_category=heading_text,
                    raw_text=raw_text[:4000],
                )
            )

        logger.info("VS Code %s: parsed %d sections", version, len(items))
        return items

    def _extract_date(self, soup: BeautifulSoup) -> datetime | None:
        """Try to extract the release date from the page meta tags."""
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            try:
                return datetime.fromisoformat(meta["content"]).astimezone(timezone.utc)
            except Exception:
                pass
        return None

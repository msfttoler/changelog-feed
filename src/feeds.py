"""Fetch and cache changelog entries from multiple sources."""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Callable

import feedparser
import requests
from bs4 import BeautifulSoup

from .models import ChangeEntry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_cache: dict[str, dict] = {}
_CACHE_TTL = 300  # seconds


def _cached(key: str, fetcher: Callable[[], list[ChangeEntry]]) -> list[ChangeEntry]:
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached["ts"] < _CACHE_TTL:
        return cached["data"]
    try:
        data = fetcher()
    except Exception:
        logger.exception("Feed fetch failed: %s", key)
        return cached["data"] if cached else []
    _cache[key] = {"ts": now, "data": data}
    return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _text(html: str) -> str:
    return BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)


_COPILOT_KW = {"copilot", "github copilot"}


# ---------------------------------------------------------------------------
# GitHub Changelog (RSS)
# ---------------------------------------------------------------------------

_GITHUB_FEED = "https://github.blog/changelog/feed/"


def fetch_github() -> list[ChangeEntry]:
    def _fetch() -> list[ChangeEntry]:
        feed = feedparser.parse(_GITHUB_FEED)
        out: list[ChangeEntry] = []
        for entry in feed.entries:
            tags = [t.term.lower() for t in getattr(entry, "tags", [])]
            link = entry.get("link", "")
            title = entry.get("title", "Untitled")
            desc = _text(entry.get("summary", ""))[:500]
            pub = (
                datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if getattr(entry, "published_parsed", None)
                else datetime.now(timezone.utc)
            )
            combined = (title + " " + " ".join(tags)).lower()
            is_copilot = any(kw in combined for kw in _COPILOT_KW)
            out.append(
                ChangeEntry(
                    id=_sha(link or title),
                    source="github",
                    title=title,
                    description=desc,
                    link=link,
                    published=pub,
                    tags=tags[:8],
                    is_copilot=is_copilot,
                )
            )
        return out

    return _cached("github", _fetch)


# ---------------------------------------------------------------------------
# VS Code Release Notes (page scrape)
# ---------------------------------------------------------------------------

_VSCODE_UPDATES = "https://code.visualstudio.com/updates"


def fetch_vscode() -> list[ChangeEntry]:
    def _fetch() -> list[ChangeEntry]:
        resp = requests.get(_VSCODE_UPDATES, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        entries: list[ChangeEntry] = []
        seen_urls: set[str] = set()
        version_urls: list[str] = []
        for a in soup.select("a[href*='/updates/v']"):
            href = a.get("href", "")
            if not href:
                continue
            if href.startswith("/"):
                href = "https://code.visualstudio.com" + href
            if href not in seen_urls:
                seen_urls.add(href)
                version_urls.append(href)

        for url in version_urls[:2]:
            version = url.rstrip("/").rsplit("/", 1)[-1]
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
            except Exception:
                logger.exception("VS Code page failed: %s", url)
                continue

            page = BeautifulSoup(r.text, "lxml")
            for h2 in page.find_all("h2"):
                heading = h2.get_text(strip=True)
                if not heading or len(heading) < 3:
                    continue

                parts: list[str] = []
                for sib in h2.find_next_siblings():
                    if sib.name == "h2":
                        break
                    t = sib.get_text(strip=True)
                    if t:
                        parts.append(t)
                    if len(parts) >= 3:
                        break

                desc = " ".join(parts)[:500]
                title = f"VS Code {version}: {heading}"
                is_copilot = "copilot" in (heading + " " + desc).lower()

                tags: list[str] = []
                if is_copilot:
                    tags.append("copilot")
                h_low = heading.lower()
                for kw, tag in [
                    ("editor", "editor"),
                    ("terminal", "terminal"),
                    ("debug", "debugging"),
                    ("extension", "extensions"),
                    ("language", "languages"),
                    ("remote", "remote"),
                    ("notebook", "notebooks"),
                    ("accessibility", "a11y"),
                ]:
                    if kw in h_low:
                        tags.append(tag)

                entries.append(
                    ChangeEntry(
                        id=_sha(url + heading),
                        source="vscode",
                        title=title,
                        description=desc,
                        link=url,
                        published=datetime.now(timezone.utc),
                        tags=tags,
                        is_copilot=is_copilot,
                    )
                )

        return entries

    return _cached("vscode", _fetch)


# ---------------------------------------------------------------------------
# Visual Studio Release Notes (page scrape)
# ---------------------------------------------------------------------------

_VS_URLS = [
    "https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-notes",
    "https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-notes-preview",
]


def fetch_visualstudio() -> list[ChangeEntry]:
    def _fetch() -> list[ChangeEntry]:
        entries: list[ChangeEntry] = []
        for url in _VS_URLS:
            is_preview = "preview" in url
            label = "Preview" if is_preview else "GA"
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
            except Exception:
                logger.exception("Visual Studio page failed: %s", url)
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            meta = soup.find("meta", property="article:published_time")
            pub = datetime.now(timezone.utc)
            if meta and meta.get("content"):
                try:
                    pub = datetime.fromisoformat(
                        meta["content"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            for h2 in soup.find_all("h2"):
                heading = h2.get_text(strip=True)
                if not heading or len(heading) < 3:
                    continue

                parts: list[str] = []
                for sib in h2.find_next_siblings():
                    if sib.name in ("h2", "h1"):
                        break
                    t = sib.get_text(strip=True)
                    if t:
                        parts.append(t)
                    if len(parts) >= 3:
                        break

                desc = " ".join(parts)[:500]
                title = f"Visual Studio ({label}): {heading}"
                is_copilot = "copilot" in (heading + " " + desc).lower()

                tags = [label.lower()]
                if is_copilot:
                    tags.append("copilot")

                entries.append(
                    ChangeEntry(
                        id=_sha(url + heading),
                        source="visualstudio",
                        title=title,
                        description=desc,
                        link=url,
                        published=pub,
                        tags=tags,
                        is_copilot=is_copilot,
                    )
                )

        return entries

    return _cached("visualstudio", _fetch)


# ---------------------------------------------------------------------------
# JetBrains IDE Blog (RSS)
# ---------------------------------------------------------------------------

_JETBRAINS_FEED = "https://blog.jetbrains.com/blog/feed/"


def fetch_jetbrains() -> list[ChangeEntry]:
    def _fetch() -> list[ChangeEntry]:
        feed = feedparser.parse(_JETBRAINS_FEED)
        out: list[ChangeEntry] = []
        for entry in feed.entries:
            link = entry.get("link", "")
            title = entry.get("title", "Untitled")
            desc = _text(entry.get("summary", ""))[:500]
            tags_raw = [t.term.lower() for t in getattr(entry, "tags", [])]
            pub = (
                datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if getattr(entry, "published_parsed", None)
                else datetime.now(timezone.utc)
            )
            combined = (title + " " + desc + " " + " ".join(tags_raw)).lower()
            is_copilot = any(kw in combined for kw in _COPILOT_KW)
            out.append(
                ChangeEntry(
                    id=_sha(link or title),
                    source="jetbrains",
                    title=title,
                    description=desc,
                    link=link,
                    published=pub,
                    tags=tags_raw[:6],
                    is_copilot=is_copilot,
                )
            )
        return out

    return _cached("jetbrains", _fetch)


# ---------------------------------------------------------------------------
# Xcode Release Notes (Apple RSS, filtered)
# ---------------------------------------------------------------------------

_XCODE_FEED = "https://developer.apple.com/news/releases/rss/releases.rss"


def fetch_xcode() -> list[ChangeEntry]:
    def _fetch() -> list[ChangeEntry]:
        feed = feedparser.parse(_XCODE_FEED)
        out: list[ChangeEntry] = []
        for entry in feed.entries:
            title = entry.get("title", "")
            if "xcode" not in title.lower():
                continue
            link = entry.get("link", "")
            desc = _text(entry.get("summary", entry.get("description", "")))[:500]
            pub = (
                datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if getattr(entry, "published_parsed", None)
                else datetime.now(timezone.utc)
            )
            is_copilot = "copilot" in (title + " " + desc).lower()
            tags = ["release"]
            if "beta" in title.lower():
                tags.append("beta")
            if "rc" in title.lower():
                tags.append("rc")
            if is_copilot:
                tags.append("copilot")
            out.append(
                ChangeEntry(
                    id=_sha(link or title),
                    source="xcode",
                    title=title,
                    description=desc,
                    link=link,
                    published=pub,
                    tags=tags,
                    is_copilot=is_copilot,
                )
            )
        return out

    return _cached("xcode", _fetch)


# ---------------------------------------------------------------------------
# Neovim Releases (GitHub API)
# ---------------------------------------------------------------------------

_NEOVIM_API = "https://api.github.com/repos/neovim/neovim/releases"


def fetch_neovim() -> list[ChangeEntry]:
    def _fetch() -> list[ChangeEntry]:
        resp = requests.get(
            _NEOVIM_API,
            headers={"Accept": "application/vnd.github+json"},
            timeout=15,
        )
        resp.raise_for_status()
        out: list[ChangeEntry] = []
        for rel in resp.json()[:10]:
            body = rel.get("body") or ""
            tag = rel.get("tag_name", "")
            name = rel.get("name") or tag
            link = rel.get("html_url", "")
            is_copilot = "copilot" in body.lower()
            tags = ["release"]
            if rel.get("prerelease"):
                tags.append("prerelease")
            if is_copilot:
                tags.append("copilot")
            pub_str = rel.get("published_at", "")
            try:
                pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pub = datetime.now(timezone.utc)
            # Truncate long markdown bodies
            desc_plain = body[:500].replace("#", "").replace("*", "").strip()
            out.append(
                ChangeEntry(
                    id=_sha(link or name),
                    source="neovim",
                    title=f"Neovim {name}",
                    description=desc_plain,
                    link=link,
                    published=pub,
                    tags=tags,
                    is_copilot=is_copilot,
                )
            )
        return out

    return _cached("neovim", _fetch)


# ---------------------------------------------------------------------------
# Eclipse IDE (Planet Eclipse blog RSS, filtered)
# ---------------------------------------------------------------------------

_ECLIPSE_FEED = "https://planet.eclipse.org/planet/rss20.xml"


def fetch_eclipse() -> list[ChangeEntry]:
    def _fetch() -> list[ChangeEntry]:
        feed = feedparser.parse(_ECLIPSE_FEED)
        out: list[ChangeEntry] = []
        eclipse_kw = {"eclipse ide", "eclipse platform", "eclipse release", "eclipse 4.", "eclipse 202"}
        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            desc = _text(entry.get("summary", ""))[:500]
            combined = (title + " " + desc).lower()
            # Keep only Eclipse IDE-relevant posts
            if not any(kw in combined for kw in eclipse_kw):
                continue
            pub = (
                datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if getattr(entry, "published_parsed", None)
                else datetime.now(timezone.utc)
            )
            is_copilot = any(kw in combined for kw in _COPILOT_KW)
            tags: list[str] = []
            if is_copilot:
                tags.append("copilot")
            out.append(
                ChangeEntry(
                    id=_sha(link or title),
                    source="eclipse",
                    title=title,
                    description=desc,
                    link=link,
                    published=pub,
                    tags=tags,
                    is_copilot=is_copilot,
                )
            )
        return out

    return _cached("eclipse", _fetch)


# ---------------------------------------------------------------------------
# Aggregate all sources
# ---------------------------------------------------------------------------

def fetch_all() -> list[ChangeEntry]:
    entries: list[ChangeEntry] = []
    for fetcher in (
        fetch_github,
        fetch_vscode,
        fetch_visualstudio,
        fetch_jetbrains,
        fetch_xcode,
        fetch_neovim,
        fetch_eclipse,
    ):
        try:
            entries.extend(fetcher())
        except Exception:
            logger.exception("Fetcher %s failed", fetcher.__name__)
    entries.sort(key=lambda e: e.published, reverse=True)
    return entries

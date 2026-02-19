"""Tests for the feed ingestors."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import feedparser
import pytest
import responses as resp_lib

from src.ingestors.github_changelog import GitHubChangelogIngestor, _infer_product_area, _stable_id
from src.ingestors.vscode import VSCodeIngestor
from src.ingestors.visual_studio import VisualStudioIngestor
from src.models import ProductArea, Source


# ── GitHub changelog tests ───────────────────────────────────────────────────

GITHUB_RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>GitHub Changelog</title>
    <link>https://github.blog/changelog</link>
    <item>
      <title>Copilot now supports GPT-4o</title>
      <link>https://github.blog/changelog/2024-copilot-gpt4o</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
      <description>GitHub Copilot has been upgraded to GPT-4o.</description>
      <category>Copilot</category>
    </item>
    <item>
      <title>Security fix for token scoping</title>
      <link>https://github.blog/changelog/2024-security-fix</link>
      <pubDate>Tue, 02 Jan 2024 12:00:00 +0000</pubDate>
      <description>Fixes a security issue with token scoping in Actions.</description>
      <category>Security</category>
    </item>
  </channel>
</rss>"""


class TestGitHubChangelogIngestor:
    def test_infer_product_area_copilot(self):
        assert _infer_product_area(["Copilot"]) == ProductArea.COPILOT

    def test_infer_product_area_security(self):
        assert _infer_product_area(["security"]) == ProductArea.SECURITY

    def test_infer_product_area_unknown(self):
        assert _infer_product_area(["unknown-tag"]) == ProductArea.OTHER

    def test_stable_id_is_deterministic(self):
        url = "https://github.blog/changelog/1"
        assert _stable_id(url) == _stable_id(url)

    def test_stable_id_differs_for_different_urls(self):
        assert _stable_id("https://a.com/1") != _stable_id("https://a.com/2")

    def test_fetch_items_parses_rss(self):
        # feedparser uses urllib (not requests) so we mock feedparser.parse directly
        parsed = feedparser.parse(GITHUB_RSS_SAMPLE)
        with patch("src.ingestors.github_changelog.feedparser.parse", return_value=parsed):
            ingestor = GitHubChangelogIngestor()
            items = ingestor.fetch_items()
        assert len(items) == 2
        assert items[0].source == Source.GITHUB
        assert items[0].title == "Copilot now supports GPT-4o"
        assert items[0].product_area == ProductArea.COPILOT

    def test_fetch_items_returns_empty_on_network_error(self):
        # Simulate feedparser returning bozo=True with no entries (network failure)
        bozo_result = MagicMock()
        bozo_result.bozo = True
        bozo_result.bozo_exception = Exception("connection error")
        bozo_result.entries = []
        with patch("src.ingestors.github_changelog.feedparser.parse", return_value=bozo_result):
            ingestor = GitHubChangelogIngestor()
            items = ingestor.fetch_items()
        assert items == []

    def test_fetch_items_with_custom_url(self):
        """Passing a custom URL is supported for testing."""
        ingestor = GitHubChangelogIngestor(feed_url="http://localhost/feed")
        assert ingestor._feed_url == "http://localhost/feed"


# ── VS Code ingestor tests ────────────────────────────────────────────────────

VSCODE_INDEX_HTML = """
<html>
<body>
<a href="/updates/v1_97">January 2025</a>
<a href="/updates/v1_96">December 2024</a>
</body>
</html>
"""

VSCODE_RELEASE_HTML = """
<html>
<head>
  <meta property="article:published_time" content="2025-01-30T00:00:00Z" />
</head>
<body>
<h1>VS Code January 2025</h1>
<h2>Remote Development</h2>
<p>Improved WSL integration for dev containers.</p>
<h2>GitHub Copilot</h2>
<p>Copilot now supports inline edits across files.</p>
<h2>Thank you</h2>
<p>Thanks to our contributors.</p>
</body>
</html>
"""


class TestVSCodeIngestor:
    @resp_lib.activate
    def test_fetch_items_parses_sections(self):
        resp_lib.add(
            resp_lib.GET,
            "https://code.visualstudio.com/updates/",
            body=VSCODE_INDEX_HTML,
            content_type="text/html",
        )
        resp_lib.add(
            resp_lib.GET,
            "https://code.visualstudio.com/updates/v1_97",
            body=VSCODE_RELEASE_HTML,
            content_type="text/html",
        )
        ingestor = VSCodeIngestor()
        items = ingestor.fetch_items()
        # "Thank you" section is excluded; 2 real sections remain
        assert len(items) == 2
        titles = [i.title for i in items]
        assert any("Remote Development" in t for t in titles)
        assert any("Copilot" in t for t in titles)
        assert all(i.source == Source.VSCODE for i in items)

    @resp_lib.activate
    def test_fetch_items_returns_empty_when_index_fails(self):
        resp_lib.add(
            resp_lib.GET,
            "https://code.visualstudio.com/updates/",
            body=Exception("network error"),
        )
        ingestor = VSCodeIngestor()
        items = ingestor.fetch_items()
        assert items == []

    @resp_lib.activate
    def test_remote_section_maps_to_devcontainers(self):
        resp_lib.add(
            resp_lib.GET,
            "https://code.visualstudio.com/updates/",
            body=VSCODE_INDEX_HTML,
            content_type="text/html",
        )
        resp_lib.add(
            resp_lib.GET,
            "https://code.visualstudio.com/updates/v1_97",
            body=VSCODE_RELEASE_HTML,
            content_type="text/html",
        )
        ingestor = VSCodeIngestor()
        items = ingestor.fetch_items()
        remote_items = [i for i in items if "Remote" in i.title]
        assert remote_items[0].product_area == ProductArea.DEVCONTAINERS


# ── Visual Studio ingestor tests ──────────────────────────────────────────────

VS_RELEASE_HTML = """
<html>
<head>
  <meta property="article:published_time" content="2025-02-01T00:00:00Z" />
</head>
<body>
<h2>17.9.0</h2>
<h3>Security fixes</h3>
<p>Patches CVE-2025-1234 in the debugger engine.</p>
<h3>GitHub Copilot improvements</h3>
<p>Copilot chat now available in all editions.</p>
</body>
</html>
"""


class TestVisualStudioIngestor:
    @resp_lib.activate
    def test_fetch_items_parses_sections(self):
        url = "https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-notes"
        resp_lib.add(resp_lib.GET, url, body=VS_RELEASE_HTML, content_type="text/html")
        ingestor = VisualStudioIngestor(release_urls=[url])
        items = ingestor.fetch_items()
        assert len(items) >= 1
        assert all(i.source == Source.VISUALSTUDIO for i in items)

    @resp_lib.activate
    def test_security_section_maps_to_security(self):
        url = "https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-notes"
        resp_lib.add(resp_lib.GET, url, body=VS_RELEASE_HTML, content_type="text/html")
        ingestor = VisualStudioIngestor(release_urls=[url])
        items = ingestor.fetch_items()
        security_items = [i for i in items if "Security" in i.title or (i.raw_category and "security" in i.raw_category.lower())]
        assert len(security_items) >= 1
        assert security_items[0].product_area == ProductArea.SECURITY

    @resp_lib.activate
    def test_fetch_items_returns_empty_on_http_error(self):
        url = "https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-notes"
        resp_lib.add(resp_lib.GET, url, status=503)
        ingestor = VisualStudioIngestor(release_urls=[url])
        items = ingestor.fetch_items()
        assert items == []

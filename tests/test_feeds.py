"""Feed coverage, failure isolation, caching, and concurrent aggregation."""

from datetime import datetime, timezone
from threading import Barrier
from unittest.mock import Mock

import pytest
import requests

from src import feeds
from src.models import ChangeEntry


@pytest.fixture(autouse=True)
def clear_cache():
    feeds._cache.clear()
    yield
    feeds._cache.clear()


def _release(**updates):
    return {
        "html_url": "https://github.com/github/app/releases/tag/v1.1.29",
        "published_at": "2026-10-13T02:39:04Z",
        "tag_name": "v1.1.29",
        "name": "v1.1.29",
        "body": "## Added\n\nParallel sessions and **canvas** fixes.",
        "draft": False,
        "prerelease": False,
        **updates,
    }


def test_app_releases_are_copilot_entries_and_cached(monkeypatch):
    response = Mock()
    response.json.return_value = [_release()]
    get = Mock(return_value=response)
    monkeypatch.setattr(feeds.requests, "get", get)

    entries = feeds.fetch_copilot_app()
    entry = entries[0]
    assert entry.source == "copilot-app"
    assert entry.title == "GitHub Copilot App v1.1.29"
    assert entry.description == "Added\n\nParallel sessions and canvas fixes."
    assert entry.published == datetime(2026, 10, 13, 2, 39, 4, tzinfo=timezone.utc)
    assert entry.is_copilot
    assert entry.surfaces == ["copilot-app"]
    assert entry.tags == ["copilot", "copilot-app", "release"]
    assert feeds.fetch_copilot_app() is entries
    get.assert_called_once_with(
        feeds._COPILOT_APP_API,
        headers={"Accept": "application/vnd.github+json"},
        timeout=15,
    )
    response.raise_for_status.assert_called_once()


def test_app_skips_drafts_and_preserves_prereleases(monkeypatch):
    response = Mock()
    response.json.return_value = [
        _release(draft=True),
        _release(name=None, body=None, prerelease=True),
    ]
    monkeypatch.setattr(feeds.requests, "get", Mock(return_value=response))
    entries = feeds.fetch_copilot_app()
    assert len(entries) == 1
    assert entries[0].title == "GitHub Copilot App v1.1.29"
    assert entries[0].description == ""
    assert "prerelease" in entries[0].tags


def test_app_http_failure_is_logged_and_keeps_cached_data(monkeypatch, caplog):
    response = Mock()
    response.json.return_value = [_release()]
    monkeypatch.setattr(feeds.requests, "get", Mock(return_value=response))
    original = feeds.fetch_copilot_app()
    feeds._cache["copilot-app"]["ts"] = 0
    response.raise_for_status.side_effect = requests.HTTPError("Rate limited")
    assert feeds.fetch_copilot_app() is original
    assert "Feed fetch failed: copilot-app" in caplog.text


@pytest.mark.parametrize(
    ("title", "summary", "tags", "expected"),
    [
        ("GitHub Copilot App update", "", [], True),
        ("Copilot desktop app improvements", "", [], True),
        ("New models", "x" * 600 + " GitHub Copilot app", [], True),
        ("New release", "", ["copilot-app"], True),
        ("GitHub Copilot CLI", "", [], False),
        ("Microsoft Copilot app", "", [], False),
        ("GitHub app authentication", "", [], False),
    ],
)
def test_github_announcements_track_app_surface(monkeypatch, title, summary, tags, expected):
    feed = feeds.feedparser.FeedParserDict(entries=[
        feeds.feedparser.FeedParserDict(
            title=title,
            link="https://github.blog/changelog/test/",
            summary=summary,
            tags=[feeds.feedparser.FeedParserDict(term=tag) for tag in tags],
            published_parsed=(2026, 10, 13, 0, 0, 0, 0, 0, 0),
        ),
    ])
    monkeypatch.setattr(feeds, "_parse_feed", Mock(return_value=feed))
    entry = feeds.fetch_github()[0]
    assert entry.source == "github"
    assert entry.surfaces == (["copilot-app"] if expected else [])
    if expected:
        assert entry.is_copilot


def test_rss_fetch_has_timeout_and_checks_status(monkeypatch):
    response = Mock(content=b"<rss><channel><title>Test</title></channel></rss>")
    get = Mock(return_value=response)
    monkeypatch.setattr(feeds.requests, "get", get)
    feeds._parse_feed("https://example.com/feed")
    get.assert_called_once_with("https://example.com/feed", timeout=15)
    response.raise_for_status.assert_called_once()


def test_fetch_all_runs_sources_concurrently_and_isolates_failure(monkeypatch, caplog):
    names = [
        "fetch_github", "fetch_copilot_app", "fetch_vscode", "fetch_visualstudio",
        "fetch_jetbrains", "fetch_xcode", "fetch_neovim", "fetch_eclipse",
    ]
    barrier = Barrier(len(names), timeout=5)

    def fetcher(index):
        def fetch():
            barrier.wait()
            if index == 2:
                raise requests.Timeout("Unavailable")
            return [ChangeEntry(
                id=str(index), source=names[index], title="Test", description="",
                link="https://example.com/",
                published=datetime(2026, 10, index + 1, tzinfo=timezone.utc),
            )]
        return fetch

    for index, name in enumerate(names):
        monkeypatch.setattr(feeds, name, fetcher(index))
    entries = feeds.fetch_all()
    assert [entry.id for entry in entries] == ["7", "6", "5", "4", "3", "1", "0"]
    assert "Unavailable" in caplog.text

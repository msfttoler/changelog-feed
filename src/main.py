"""Build static changelog data for GitHub Pages."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .feeds import fetch_all
from .parity import get_parity_matrix
from .retention import filter_recent
from .scorer import score_entry
from .summarizer import add_summaries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build(out_dir: Path | None = None) -> None:
    out = out_dir or Path(__file__).resolve().parent.parent / "docs"
    out.mkdir(exist_ok=True)

    logger.info("Fetching feeds…")
    entries = fetch_all()
    logger.info("Fetched %d entries", len(entries))

    entries = filter_recent(entries)
    logger.info("Retained %d entries within 3-month window", len(entries))

    scored = [score_entry(e) for e in entries]
    scored.sort(key=lambda e: (-e.score, -e.published.timestamp()))

    logger.info("Generating AI summaries…")
    scored = add_summaries(scored)

    sources = {
        "github": {
            "name": "GitHub Blog – Changelog",
            "url": "https://github.blog/changelog/",
            "feed": "https://github.blog/changelog/feed/",
        },
        "vscode": {
            "name": "Visual Studio Code – Release Notes",
            "url": "https://code.visualstudio.com/updates",
        },
        "visualstudio": {
            "name": "Visual Studio 2022 – Release Notes",
            "url": "https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-notes",
        },
        "jetbrains": {
            "name": "JetBrains Blog",
            "url": "https://blog.jetbrains.com/blog/",
            "feed": "https://blog.jetbrains.com/blog/feed/",
        },
        "xcode": {
            "name": "Apple Developer – Xcode Releases",
            "url": "https://developer.apple.com/xcode/",
            "feed": "https://developer.apple.com/news/releases/rss/releases.rss",
        },
        "neovim": {
            "name": "Neovim – GitHub Releases",
            "url": "https://github.com/neovim/neovim/releases",
        },
        "eclipse": {
            "name": "Planet Eclipse",
            "url": "https://planet.eclipse.org/planet/",
            "feed": "https://planet.eclipse.org/planet/rss20.xml",
        },
    }

    data = {
        "entries": [e.model_dump(mode="json") for e in scored],
        "parity": get_parity_matrix(),
        "sources": sources,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    (out / "data.json").write_text(json.dumps(data, indent=2))
    logger.info("Wrote %d entries → %s", len(scored), out / "data.json")


if __name__ == "__main__":
    build()

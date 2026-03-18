"""Build static changelog data for GitHub Pages."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .feeds import fetch_all
from .parity import get_parity_matrix
from .scorer import score_entry

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

    scored = [score_entry(e) for e in entries]
    scored.sort(key=lambda e: (-e.score, -e.published.timestamp()))

    data = {
        "entries": [e.model_dump(mode="json") for e in scored],
        "parity": get_parity_matrix(),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    (out / "data.json").write_text(json.dumps(data, indent=2))
    logger.info("Wrote %d entries → %s", len(scored), out / "data.json")


if __name__ == "__main__":
    build()

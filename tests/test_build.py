"""Integration test for the full build pipeline."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src.main import build
from src.models import ChangeEntry


def _fake_entries(count=10, include_old=False):
    """Generate fake entries, optionally including old ones beyond 90 days."""
    now = datetime.now(timezone.utc)
    entries = []
    for i in range(count):
        days_ago = i * 10  # 0, 10, 20, …
        entries.append(
            ChangeEntry(
                id=f"fake-{i}",
                source=["github", "vscode", "jetbrains"][i % 3],
                title=f"Test entry {i}",
                description=f"Description for entry {i}",
                link=f"https://example.com/{i}",
                published=now - timedelta(days=days_ago),
            )
        )
    if include_old:
        for j in range(3):
            entries.append(
                ChangeEntry(
                    id=f"old-{j}",
                    source="github",
                    title=f"Old entry {j}",
                    description="This is very old",
                    link=f"https://example.com/old/{j}",
                    published=now - timedelta(days=120 + j * 30),
                )
            )
    return entries


class TestBuildPipeline:
    def test_build_writes_data_json(self, tmp_path):
        with (
            patch("src.main.fetch_all", return_value=_fake_entries()),
            patch("src.main.add_summaries", side_effect=lambda x: x),
        ):
            build(out_dir=tmp_path)

        data_file = tmp_path / "data.json"
        assert data_file.exists()
        data = json.loads(data_file.read_text())
        assert "entries" in data
        assert "parity" in data
        assert "sources" in data
        assert "built_at" in data

    def test_entries_are_scored(self, tmp_path):
        with (
            patch("src.main.fetch_all", return_value=_fake_entries()),
            patch("src.main.add_summaries", side_effect=lambda x: x),
        ):
            build(out_dir=tmp_path)

        data = json.loads((tmp_path / "data.json").read_text())
        for entry in data["entries"]:
            assert "score" in entry
            assert "severity" in entry
            assert entry["severity"] in ("low", "medium", "high", "critical")

    def test_entries_sorted_by_score_desc(self, tmp_path):
        with (
            patch("src.main.fetch_all", return_value=_fake_entries()),
            patch("src.main.add_summaries", side_effect=lambda x: x),
        ):
            build(out_dir=tmp_path)

        data = json.loads((tmp_path / "data.json").read_text())
        scores = [e["score"] for e in data["entries"]]
        assert scores == sorted(scores, reverse=True)

    def test_old_entries_filtered_out(self, tmp_path):
        with (
            patch("src.main.fetch_all", return_value=_fake_entries(5, include_old=True)),
            patch("src.main.add_summaries", side_effect=lambda x: x),
        ):
            build(out_dir=tmp_path)

        data = json.loads((tmp_path / "data.json").read_text())
        ids = [e["id"] for e in data["entries"]]
        # Old entries (>90 days old) should be excluded
        assert not any(eid.startswith("old-") for eid in ids)

    def test_recent_entries_preserved(self, tmp_path):
        with (
            patch("src.main.fetch_all", return_value=_fake_entries(5, include_old=True)),
            patch("src.main.add_summaries", side_effect=lambda x: x),
        ):
            build(out_dir=tmp_path)

        data = json.loads((tmp_path / "data.json").read_text())
        ids = [e["id"] for e in data["entries"]]
        assert any(eid.startswith("fake-") for eid in ids)

    def test_parity_structure_present(self, tmp_path):
        with (
            patch("src.main.fetch_all", return_value=[]),
            patch("src.main.add_summaries", side_effect=lambda x: x),
        ):
            build(out_dir=tmp_path)

        data = json.loads((tmp_path / "data.json").read_text())
        parity = data["parity"]
        assert "ides" in parity
        assert "categories" in parity
        assert len(parity["ides"]) == 7

    def test_sources_metadata(self, tmp_path):
        with (
            patch("src.main.fetch_all", return_value=[]),
            patch("src.main.add_summaries", side_effect=lambda x: x),
        ):
            build(out_dir=tmp_path)

        data = json.loads((tmp_path / "data.json").read_text())
        sources = data["sources"]
        expected_keys = {"github", "vscode", "visualstudio", "jetbrains", "xcode", "neovim", "eclipse"}
        assert set(sources.keys()) == expected_keys
        for key, src in sources.items():
            assert "name" in src
            assert "url" in src

    def test_built_at_is_iso_timestamp(self, tmp_path):
        with (
            patch("src.main.fetch_all", return_value=[]),
            patch("src.main.add_summaries", side_effect=lambda x: x),
        ):
            build(out_dir=tmp_path)

        data = json.loads((tmp_path / "data.json").read_text())
        # Should parse as ISO datetime
        dt = datetime.fromisoformat(data["built_at"])
        assert dt.tzinfo is not None

    def test_creates_output_dir(self, tmp_path):
        out = tmp_path / "output"
        with (
            patch("src.main.fetch_all", return_value=[]),
            patch("src.main.add_summaries", side_effect=lambda x: x),
        ):
            build(out_dir=out)

        assert (out / "data.json").exists()

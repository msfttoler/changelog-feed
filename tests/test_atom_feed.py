"""Tests for the Atom feed generator."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.atom_feed import generate_atom
from src.models import ChangeEntry


def _entry(**overrides) -> ChangeEntry:
    defaults = dict(
        id="abc123",
        source="github",
        title="Test entry",
        description="A test changelog entry",
        link="https://example.com/changelog",
        published=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc),
        tags=["copilot", "security"],
        is_copilot=True,
        score=80,
        severity="critical",
        ai_summary="Important security fix.",
        highlight=True,
    )
    defaults.update(overrides)
    return ChangeEntry(**defaults)


class TestGenerateAtom:
    def test_returns_xml_string(self):
        xml = generate_atom([_entry()])
        assert xml.startswith("<?xml version")
        assert "<feed" in xml

    def test_contains_feed_metadata(self):
        xml = generate_atom([_entry()])
        assert "<title>Developer Productivity Changelog Feed</title>" in xml
        assert 'rel="self"' in xml
        assert 'type="application/atom+xml"' in xml

    def test_contains_entry(self):
        xml = generate_atom([_entry(title="My Title")])
        assert "<title>My Title</title>" in xml
        assert "urn:changelog:abc123" in xml

    def test_entry_has_link(self):
        xml = generate_atom([_entry(link="https://example.com/cl")])
        assert 'href="https://example.com/cl"' in xml

    def test_entry_has_summary_with_ai(self):
        xml = generate_atom([_entry(ai_summary="AI says this.", description="Desc here.")])
        root = ET.fromstring(xml)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        summary = root.find(".//a:entry/a:summary", ns)
        assert summary is not None
        assert "AI says this." in summary.text
        assert "Desc here." in summary.text

    def test_entry_has_categories(self):
        xml = generate_atom([_entry(tags=["security", "copilot"])])
        root = ET.fromstring(xml)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        cats = root.findall(".//a:entry/a:category", ns)
        terms = [c.get("term") for c in cats]
        assert "security" in terms
        assert "copilot" in terms

    def test_limits_to_100_entries(self):
        entries = [_entry(id=f"e{i}") for i in range(150)]
        xml = generate_atom(entries)
        root = ET.fromstring(xml)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        assert len(root.findall("a:entry", ns)) == 100

    def test_empty_entries(self):
        xml = generate_atom([])
        root = ET.fromstring(xml)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        assert len(root.findall("a:entry", ns)) == 0
        assert root.find("a:title", ns).text is not None

    def test_writes_to_file(self, tmp_path: Path):
        out = tmp_path / "feed.xml"
        xml = generate_atom([_entry()], out_path=out)
        assert out.exists()
        content = out.read_text()
        assert content == xml

    def test_built_at_in_updated(self):
        ts = "2026-03-18T12:00:00+00:00"
        xml = generate_atom([_entry()], built_at=ts)
        root = ET.fromstring(xml)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        updated = root.find("a:updated", ns)
        assert updated.text == ts

    def test_no_ai_summary_uses_description(self):
        xml = generate_atom([_entry(ai_summary="", description="Just desc")])
        root = ET.fromstring(xml)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        summary = root.find(".//a:entry/a:summary", ns)
        assert summary.text == "Just desc"

    def test_valid_xml_parse(self):
        entries = [_entry(id=f"e{i}", title=f"Entry {i}") for i in range(10)]
        xml = generate_atom(entries)
        # Should not raise
        root = ET.fromstring(xml)
        assert root.tag == "{http://www.w3.org/2005/Atom}feed"

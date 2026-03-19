"""Generate an Atom feed from changelog entries."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from .models import ChangeEntry

_FEED_ID = "https://msfttoler.github.io/changelog-feed/"
_FEED_TITLE = "Developer Productivity Changelog Feed"
_FEED_SUBTITLE = "IDE & Copilot changelog tracker — scored by importance"
_FEED_LINK = "https://msfttoler.github.io/changelog-feed/"
_FEED_SELF = "https://msfttoler.github.io/changelog-feed/feed.xml"

_NS = "http://www.w3.org/2005/Atom"


def generate_atom(
    entries: list[ChangeEntry],
    built_at: str | None = None,
    out_path: Path | None = None,
) -> str:
    """Build an Atom XML feed string and optionally write it to *out_path*."""
    feed = Element("feed", xmlns=_NS)

    SubElement(feed, "title").text = _FEED_TITLE
    SubElement(feed, "subtitle").text = _FEED_SUBTITLE
    SubElement(feed, "id").text = _FEED_ID
    SubElement(feed, "link", href=_FEED_LINK, rel="alternate", type="text/html")
    SubElement(feed, "link", href=_FEED_SELF, rel="self", type="application/atom+xml")

    updated = built_at or datetime.now(timezone.utc).isoformat()
    SubElement(feed, "updated").text = updated

    author = SubElement(feed, "author")
    SubElement(author, "name").text = "Changelog Feed Bot"

    for entry in entries[:100]:
        e = SubElement(feed, "entry")
        SubElement(e, "id").text = f"urn:changelog:{entry.id}"
        SubElement(e, "title").text = entry.title
        SubElement(e, "link", href=entry.link, rel="alternate")
        SubElement(e, "published").text = entry.published.isoformat()
        SubElement(e, "updated").text = entry.published.isoformat()

        summary_parts = []
        if entry.ai_summary:
            summary_parts.append(entry.ai_summary)
        if entry.description:
            summary_parts.append(entry.description)
        SubElement(e, "summary").text = " — ".join(summary_parts) or entry.title

        for tag in entry.tags[:6]:
            SubElement(e, "category", term=tag)

    xml_bytes = tostring(feed, encoding="unicode", xml_declaration=False)
    xml_str = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_bytes

    if out_path:
        out_path.write_text(xml_str, encoding="utf-8")

    return xml_str

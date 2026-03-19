"""Data models for changelog entries."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ChangeEntry(BaseModel):
    """A single changelog entry from any source."""

    id: str
    source: str
    title: str
    description: str
    link: str
    published: datetime
    tags: list[str] = []
    is_copilot: bool = False
    score: int = 0
    severity: str = "low"
    ai_summary: str = ""
    highlight: bool = False

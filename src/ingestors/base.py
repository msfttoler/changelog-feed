"""Abstract base class for all feed ingestors."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import ChangeItem


class BaseIngestor(ABC):
    """Fetches and normalizes items from a single signal source.

    Each concrete ingestor is responsible for:
    1. Fetching raw data from its source URL(s).
    2. Normalising each entry into a :class:`~src.models.ChangeItem`.
    3. Returning the resulting list – newest items first where possible.
    """

    @abstractmethod
    def fetch_items(self) -> list[ChangeItem]:
        """Fetch and normalize items from the source.

        Returns
        -------
        list[ChangeItem]
            Normalized change items, newest first.
        """

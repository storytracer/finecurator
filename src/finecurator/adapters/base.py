"""Abstract base class that all source adapters must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, ClassVar

from finecurator.models import Record
from finecurator.registry import register


class BaseAdapter(ABC):
    """Contract for source-specific adapters.

    Each cultural heritage source gets its own adapter subclass.
    Subclasses **must** set the ``name`` class variable. Registration
    into the global adapter registry happens automatically when a
    concrete (non-abstract) subclass is created.
    """

    name: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "name") and not getattr(cls, "__abstractmethods__", None):
            register(cls.name, cls)

    @abstractmethod
    async def discover(self, **kwargs: Any) -> AsyncIterator[Record]:
        """Discover records available from this source.

        Yields Record objects in the DISCOVERED stage.
        """
        ...

    @abstractmethod
    async def download(self, record: Record, output_dir: Path) -> Record:
        """Download raw data for a single record.

        Returns the record updated to DOWNLOADED stage.
        """
        ...

    @abstractmethod
    async def process(self, record: Record, output_dir: Path) -> Record:
        """Process raw data into a normalized format.

        Returns the record updated to PROCESSED stage.
        """
        ...

    @abstractmethod
    async def extract_metadata(self, record: Record) -> Record:
        """Extract and normalize metadata for a record."""
        ...

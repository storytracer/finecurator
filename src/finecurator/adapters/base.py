"""Abstract base class that all source adapters must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

from finecurator.models import Record
from finecurator.registry import register


class BaseAdapter(ABC):
    """Contract for source-specific adapters.

    Each cultural heritage source (a digital library, archive, museum
    API, etc.) gets its own adapter subclass.  Adapters encapsulate all
    source-specific concerns -- API authentication, pagination, rate
    limiting, format quirks -- while exposing a uniform interface that
    the pipeline and CLI can drive.

    Subclasses **must** set the ``name`` class variable to a unique
    string identifier.  Registration into the global adapter registry
    happens automatically when a concrete (non-abstract) subclass is
    created.
    """

    name: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Only register concrete adapters (no remaining abstract methods).
        if hasattr(cls, "name") and not getattr(cls, "__abstractmethods__", None):
            register(cls.name, cls)

    @abstractmethod
    def discover(self, **kwargs: Any) -> Iterator[Record]:
        """Discover records available from this source.

        Yields :class:`Record` objects in the ``DISCOVERED`` stage.
        """
        ...

    @abstractmethod
    def download(self, record: Record, output_dir: Path) -> Record:
        """Download raw data for a single record.

        Returns the record updated to ``DOWNLOADED`` stage with
        ``local_paths`` populated.
        """
        ...

    @abstractmethod
    def process(self, record: Record, output_dir: Path) -> Record:
        """Process raw data into a normalized format.

        Returns the record updated to ``PROCESSED`` stage.
        """
        ...

    @abstractmethod
    def extract_metadata(self, record: Record) -> Record:
        """Extract and normalize metadata for a record."""
        ...

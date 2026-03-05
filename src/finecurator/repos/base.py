"""Abstract base class that all repo modules must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, ClassVar

from finecurator.models import Record
from finecurator.registry import register


class BaseRepo(ABC):
    """Contract for repo modules.

    Each cultural heritage repo gets its own subclass.
    Subclasses **must** set the ``name`` class variable. Registration
    into the global registry happens automatically when a concrete
    (non-abstract) subclass is created.
    """

    name: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "name") and not getattr(cls, "__abstractmethods__", None):
            register(cls.name, cls)

    @abstractmethod
    async def discover(self, **kwargs: Any) -> AsyncIterator[Record]:
        """Discover records available from this repo.

        Yields Record objects in the DISCOVERED stage.
        """
        ...

    @abstractmethod
    async def download(self, record: Record, output_dir: Path) -> Record:
        """Download raw data for a single record.

        Returns the record updated to DOWNLOADED stage.
        """
        ...


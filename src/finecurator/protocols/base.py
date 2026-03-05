"""Abstract base class for protocol clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path

from finecurator.models import Item


class BaseProtocol(ABC):
    """Base class for protocol clients.

    Protocol clients own the conversion from format-specific models
    (e.g. IIIFManifest, METSDocument) to the universal Item tree.
    """

    @abstractmethod
    async def discover(self, url: str) -> AsyncIterator[Item]:
        """Discover items from a URL.

        Yields Item trees (potentially nested with children).
        """
        ...

    @abstractmethod
    async def download_resources(self, item: Item, output_dir: Path) -> int:
        """Download all resources for an Item tree.

        Recursively walks the Item tree, downloads all Resource objects,
        and updates their local_path fields.

        Returns the number of successfully downloaded resources.
        """
        ...

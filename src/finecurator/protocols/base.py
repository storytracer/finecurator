"""Abstract base class for protocol clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path

from finecurator.models import CreativeWork


class BaseProtocol(ABC):
    """Base class for protocol clients.

    Protocol clients own the conversion from format-specific models
    (e.g. IIIFManifest, METSDocument) to CreativeWork trees.
    """

    @abstractmethod
    async def discover(self, url: str) -> AsyncIterator[CreativeWork]:
        """Discover works from a URL.

        Yields CreativeWork trees (potentially nested with parts).
        """
        ...

    @abstractmethod
    async def download_resources(self, work: CreativeWork, output_dir: Path) -> int:
        """Download all media for a CreativeWork tree.

        Recursively walks the tree, downloads all MediaObject files,
        and updates their local_path fields.

        Returns the number of successfully downloaded files.
        """
        ...

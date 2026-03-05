"""OAI-PMH protocol client (stub)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from finecurator.models import CreativeWork
from finecurator.protocols.base import BaseProtocol


class OAIPMHClient(BaseProtocol):
    """Protocol client for OAI-PMH. Not yet implemented."""

    async def discover(self, url: str) -> AsyncIterator[CreativeWork]:
        raise NotImplementedError("OAI-PMH client not yet implemented")
        yield  # pragma: no cover — make this a generator

    async def download_resources(self, work: CreativeWork, output_dir: Path) -> int:
        raise NotImplementedError("OAI-PMH client not yet implemented")

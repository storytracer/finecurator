"""Generic IIIF adapter.

Works with any IIIF-compliant manifest (v2 or v3). Delegates to
the IIIFClient protocol for discovery and downloading.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from finecurator.adapters.base import BaseAdapter
from finecurator.http.client import HttpConfig
from finecurator.models import PipelineStage, Record
from finecurator.protocols.iiif import IIIFClient

logger = logging.getLogger(__name__)


class IIIFAdapter(BaseAdapter):
    """Adapter for any IIIF Presentation API manifest."""

    name = "iiif-generic"

    def __init__(self, config: HttpConfig | None = None):
        self.config = config or HttpConfig()
        self.client = IIIFClient(self.config)

    async def discover(self, **kwargs: Any) -> AsyncIterator[Record]:
        url = kwargs.get("url")
        if not url:
            raise ValueError("IIIF adapter requires a 'url' keyword argument")

        async for item in self.client.discover(url):
            yield Record(
                id=item.item_id,
                source=url,
                stage=PipelineStage.DISCOVERED,
                item=item,
            )

    async def download(self, record: Record, output_dir: Path) -> Record:
        if record.item is None:
            record.errors.append("No item to download")
            return record

        try:
            count = await self.client.download_resources(record.item, output_dir)
            record.item.local_dir = output_dir
            record.stage = PipelineStage.DOWNLOADED
            logger.info(f"Downloaded {count} resources for {record.id}")
        except Exception as e:
            record.errors.append(f"Download failed: {e}")

        return record

    async def process(self, record: Record, output_dir: Path) -> Record:
        # Placeholder: IIIF images don't need further processing by default
        record.stage = PipelineStage.PROCESSED
        return record

    async def extract_metadata(self, record: Record) -> Record:
        # Metadata is already extracted during discover from the manifest
        return record

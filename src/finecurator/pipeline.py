"""Pipeline orchestration: discover -> download -> process -> clean -> validate -> output."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from pathlib import Path
from typing import Any

from finecurator.models import PipelineContext, PipelineStage, Record
from finecurator.registry import get_adapter


class Pipeline:
    """Orchestrates the full curation pipeline.

    Each stage is independently runnable. The pipeline can execute
    end-to-end via ``run`` or stage-by-stage via individual methods.
    All stages are async.
    """

    STAGES = [
        PipelineStage.DISCOVERED,
        PipelineStage.DOWNLOADED,
        PipelineStage.PROCESSED,
        PipelineStage.CLEANED,
        PipelineStage.VALIDATED,
        PipelineStage.OUTPUT,
    ]

    def __init__(
        self,
        adapter_name: str,
        output_dir: Path,
        *,
        config: dict[str, Any] | None = None,
    ) -> None:
        adapter_cls = get_adapter(adapter_name)
        self.adapter = adapter_cls()
        self.output_dir = Path(output_dir)
        self.state_dir = self.output_dir / ".state"
        self.context = PipelineContext(
            adapter_name=adapter_name,
            output_dir=self.output_dir,
            state_dir=self.state_dir,
            config=config or {},
        )

    async def run(self, **kwargs: Any) -> AsyncIterator[Record]:
        """Run the full pipeline end-to-end."""
        records = self.discover(**kwargs)
        records = self.download(records)
        records = self.process(records)
        records = self.clean(records)
        records = self.validate(records)
        async for record in self.output(records):
            yield record

    async def discover(self, **kwargs: Any) -> AsyncIterator[Record]:
        """Run the discover stage via the adapter."""
        async for record in self.adapter.discover(**kwargs):
            yield record

    async def download(self, records: AsyncIterable[Record]) -> AsyncIterator[Record]:
        """Run the download stage via the adapter."""
        download_dir = self.output_dir / "raw"
        async for record in records:
            yield await self.adapter.download(record, download_dir)

    async def process(self, records: AsyncIterable[Record]) -> AsyncIterator[Record]:
        """Run the process stage via the adapter."""
        process_dir = self.output_dir / "processed"
        async for record in records:
            yield await self.adapter.process(record, process_dir)

    async def clean(self, records: AsyncIterable[Record]) -> AsyncIterator[Record]:
        """Run the clean stage (placeholder)."""
        async for record in records:
            yield record

    async def validate(self, records: AsyncIterable[Record]) -> AsyncIterator[Record]:
        """Run the validate stage (placeholder)."""
        async for record in records:
            yield record

    async def output(self, records: AsyncIterable[Record]) -> AsyncIterator[Record]:
        """Run the output stage (placeholder)."""
        async for record in records:
            yield record

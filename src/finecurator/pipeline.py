"""Pipeline orchestration: discover -> download -> process."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from pathlib import Path
from typing import Any

from finecurator.models import PipelineContext, PipelineStage, Record
from finecurator.registry import get_repo


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
    ]

    def __init__(
        self,
        repo_name: str,
        output_dir: Path,
        *,
        config: dict[str, Any] | None = None,
    ) -> None:
        repo_cls = get_repo(repo_name)
        self.repo = repo_cls()
        self.output_dir = Path(output_dir)
        self.state_dir = self.output_dir / ".state"
        self.context = PipelineContext(
            repo_name=repo_name,
            output_dir=self.output_dir,
            state_dir=self.state_dir,
            config=config or {},
        )

    async def run(self, **kwargs: Any) -> AsyncIterator[Record]:
        """Run the full pipeline end-to-end."""
        records = self.discover(**kwargs)
        records = self.download(records)
        async for record in self.process(records):
            yield record

    async def discover(self, **kwargs: Any) -> AsyncIterator[Record]:
        """Run the discover stage via the repo."""
        async for record in self.repo.discover(**kwargs):
            yield record

    async def download(self, records: AsyncIterable[Record]) -> AsyncIterator[Record]:
        """Run the download stage via the repo."""
        download_dir = self.output_dir / "raw"
        async for record in records:
            yield await self.repo.download(record, download_dir)

    async def process(self, records: AsyncIterable[Record]) -> AsyncIterator[Record]:
        """Run the process stage via the repo."""
        process_dir = self.output_dir / "processed"
        async for record in records:
            yield await self.repo.process(record, process_dir)


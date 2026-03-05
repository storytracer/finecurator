"""Pipeline orchestration: discover -> download -> export."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterable, AsyncIterator
from pathlib import Path
from typing import Any

from finecurator.export import Exporter, get_exporter
from finecurator.models import PipelineContext, PipelineStage, Record
from finecurator.registry import get_repo
from finecurator.state import StateManager

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates the curation pipeline with persistent state.

    Stages are idempotent — if a record has already completed a stage
    (according to the state directory), it is skipped automatically.
    Dependencies are resolved: download auto-discovers if needed.
    """

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
        self.state = StateManager(self.state_dir)
        self.context = PipelineContext(
            repo_name=repo_name,
            output_dir=self.output_dir,
            state_dir=self.state_dir,
            config=config or {},
        )

    async def run(self, *, force: bool = False, **kwargs: Any) -> AsyncIterator[Record]:
        """Run discover + download (default end-to-end)."""
        records = self.discover(force=force, **kwargs)
        async for record in self.download(records, force=force):
            yield record

    async def discover(self, *, force: bool = False, **kwargs: Any) -> AsyncIterator[Record]:
        """Run the discover stage, with caching via state."""
        url = kwargs.get("url")

        if not force and url:
            record_id = self.state.get_id_for_source(url)
            if record_id:
                cached = self.state.load_at_stage(record_id, PipelineStage.DISCOVERED)
                if cached:
                    logger.info("Using cached discovery for %s", record_id)
                    yield cached
                    return

        async for record in self.repo.discover(**kwargs):
            self.state.save(record)
            if url:
                self.state.map_source(url, record.id)
            yield record

    async def download(
        self,
        records: AsyncIterable[Record],
        *,
        force: bool = False,
    ) -> AsyncIterator[Record]:
        """Run the download stage, skipping already-downloaded records."""
        async for record in records:
            if not force:
                cached = self.state.load_at_stage(record.id, PipelineStage.DOWNLOADED)
                if cached:
                    logger.info("Skipping download for %s (already downloaded)", record.id)
                    yield cached
                    continue

            result = await self.repo.download(record, self.output_dir)
            self.state.save(result)
            yield result

    async def export(
        self,
        records: AsyncIterable[Record],
        *,
        export_format: str = "png",
        force: bool = False,
    ) -> AsyncIterator[Record]:
        """Run the export stage, skipping already-exported records."""
        exporter = get_exporter(export_format)

        async for record in records:
            if not force:
                cached = self.state.load_at_stage(record.id, PipelineStage.EXPORTED)
                if cached:
                    logger.info("Skipping export for %s (already exported)", record.id)
                    yield cached
                    continue

            result = await exporter.export(record, self.output_dir)
            self.state.save(result)
            yield result

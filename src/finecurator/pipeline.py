"""Pipeline orchestration: discover -> download -> process -> clean -> validate -> output."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from finecurator.models import PipelineContext, PipelineStage, Record
from finecurator.registry import get_adapter


class Pipeline:
    """Orchestrates the full curation pipeline.

    Each stage is independently runnable.  The pipeline can execute
    end-to-end via :meth:`run` or stage-by-stage via the individual
    methods.
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

    def run(self, **kwargs: Any) -> Iterator[Record]:
        """Run the full pipeline end-to-end."""
        records = self.discover(**kwargs)
        records = self.download(records)
        records = self.process(records)
        records = self.clean(records)
        records = self.validate(records)
        yield from self.output(records)

    def discover(self, **kwargs: Any) -> Iterator[Record]:
        """Run the discover stage via the adapter."""
        yield from self.adapter.discover(**kwargs)

    def download(self, records: Iterable[Record]) -> Iterator[Record]:
        """Run the download stage via the adapter."""
        download_dir = self.output_dir / "raw"
        for record in records:
            yield self.adapter.download(record, download_dir)

    def process(self, records: Iterable[Record]) -> Iterator[Record]:
        """Run the process stage via the adapter."""
        process_dir = self.output_dir / "processed"
        for record in records:
            yield self.adapter.process(record, process_dir)

    def clean(self, records: Iterable[Record]) -> Iterator[Record]:
        """Run the clean stage. Uses shared cleaning utilities."""
        # Placeholder -- will compose shared cleaning utils here.
        yield from records

    def validate(self, records: Iterable[Record]) -> Iterator[Record]:
        """Run the validate stage. Uses shared validation utilities."""
        # Placeholder -- will compose shared validation utils here.
        yield from records

    def output(self, records: Iterable[Record]) -> Iterator[Record]:
        """Run the output stage. Formats and writes the curated dataset."""
        # Placeholder -- will implement output formatting here.
        yield from records

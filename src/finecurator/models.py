"""Core data models that flow through the curation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PipelineStage(Enum):
    """Tracks which pipeline stage a record has completed."""

    DISCOVERED = "discovered"
    DOWNLOADED = "downloaded"
    PROCESSED = "processed"
    CLEANED = "cleaned"
    VALIDATED = "validated"
    OUTPUT = "output"


@dataclass
class Metadata:
    """Structured metadata for a cultural heritage record.

    Common fields are explicit attributes. Source-specific or
    non-standard fields go in ``extra``.
    """

    title: str | None = None
    creator: str | None = None
    date: str | None = None
    language: str | None = None
    source_url: str | None = None
    license: str | None = None
    rights: str | None = None
    description: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Record:
    """A single item flowing through the curation pipeline.

    Records accumulate data as they pass through stages: discovery
    populates the ID and source metadata, downloading adds local file
    paths, processing adds derived data, and so on.
    """

    id: str
    source: str
    stage: PipelineStage = PipelineStage.DISCOVERED
    metadata: Metadata = field(default_factory=Metadata)
    local_paths: dict[str, Path] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineContext:
    """Runtime context passed through pipeline stages."""

    adapter_name: str
    output_dir: Path
    state_dir: Path
    config: dict[str, Any] = field(default_factory=dict)

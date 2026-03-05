"""Core data models for the finecurator pipeline.

Built on Schema.org vocabulary. The central class is CreativeWork — a universal
node that forms trees via parts/is_part_of (Schema.org hasPart/isPartOf).
MediaObject represents downloadable files attached to works.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PipelineStage(Enum):
    """Tracks which pipeline stage a record has completed."""

    DISCOVERED = "discovered"
    DOWNLOADED = "downloaded"
    EXPORTED = "exported"


_STAGE_ORDER: dict[PipelineStage, int] = {
    PipelineStage.DISCOVERED: 0,
    PipelineStage.DOWNLOADED: 1,
    PipelineStage.EXPORTED: 2,
}


def stage_gte(current: PipelineStage, required: PipelineStage) -> bool:
    """Check if *current* stage is at or past *required*."""
    return _STAGE_ORDER[current] >= _STAGE_ORDER[required]


class Person(BaseModel):
    """A person or organization (Schema.org Person/Organization).

    Uses a ``type`` string to distinguish between "Person" and "Organization".
    """

    type: str = "Person"
    name: str
    url: str | None = None


class MediaObject(BaseModel):
    """A downloadable file (Schema.org MediaObject).

    Maps to schema:MediaObject with practical extensions for downloading.
    """

    content_url: str
    encoding_format: str | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    content_size: int | None = None
    local_path: Path | None = None
    fallback_url: str | None = None


class CreativeWork(BaseModel):
    """A Schema.org CreativeWork — the universal node in the item hierarchy.

    Everything is a CreativeWork: a book, collection, volume, page, etc.
    The ``type`` string specifies the Schema.org type (e.g. "Book", "Collection",
    "ImageObject"). Properties use Schema.org naming conventions.
    """

    id: str
    type: str = "CreativeWork"
    name: str | None = None
    url: str | None = None
    position: int | None = None

    # Schema.org properties
    creator: list[Person] = Field(default_factory=list)
    date_published: str | None = None
    in_language: str | None = None
    license: str | None = None
    description: str | None = None
    publisher: Person | None = None
    contributor: list[Person] = Field(default_factory=list)
    identifier: str | None = None
    keywords: list[str] = Field(default_factory=list)

    # Content
    text: str | None = None
    encoding_format: str | None = None

    # Hierarchy (hasPart / isPartOf)
    parts: list[CreativeWork] = Field(default_factory=list)
    is_part_of: CreativeWork | None = Field(default=None, repr=False, exclude=True)

    # Associated media
    associated_media: list[MediaObject] = Field(default_factory=list)

    # Local filesystem
    local_dir: Path | None = None

    # Extension point
    extra: dict[str, Any] = Field(default_factory=dict)

    def add_part(self, part: CreativeWork) -> None:
        """Append a child part and set its isPartOf back-reference."""
        part.is_part_of = self
        self.parts.append(part)

    def get_parts_by_type(self, schema_type: str) -> list[CreativeWork]:
        """Return direct parts matching the given Schema.org type."""
        return [p for p in self.parts if p.type == schema_type]

    @property
    def all_media(self) -> list[MediaObject]:
        """Recursively collect all media from this work and descendants."""
        result = list(self.associated_media)
        for part in self.parts:
            result.extend(part.all_media)
        return result

    @property
    def all_parts(self) -> list[CreativeWork]:
        """Recursively flatten all descendant parts."""
        result: list[CreativeWork] = []
        for part in self.parts:
            result.append(part)
            result.extend(part.all_parts)
        return result


class Record(BaseModel):
    """Pipeline envelope wrapping a CreativeWork as it flows through stages."""

    id: str
    source: str
    stage: PipelineStage = PipelineStage.DISCOVERED
    work: CreativeWork | None = None
    errors: list[str] = Field(default_factory=list)


class PipelineContext(BaseModel):
    """Runtime context passed through pipeline stages."""

    repo_name: str
    output_dir: Path
    state_dir: Path
    config: dict[str, Any] = Field(default_factory=dict)

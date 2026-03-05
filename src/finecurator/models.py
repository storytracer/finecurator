"""Core data models for the finecurator pipeline.

Follows a single-class hierarchy: everything is an Item with a work_type enum.
Items form trees via children/parent. Resources are downloadable files attached
to items. Providers track data provenance (EDM ore:Aggregation pattern).
Field names align with Dublin Core / Schema.org conventions.
"""

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


class WorkType(Enum):
    """What kind of cultural heritage item this is."""

    WORK = "work"
    SERIES = "series"
    COLLECTION = "collection"
    VOLUME = "volume"
    ISSUE = "issue"
    EDITION = "edition"
    DOCUMENT = "document"
    PART = "part"
    PAGE = "page"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"


class ResourceRole(Enum):
    """The role a resource plays for its parent item."""

    IMAGE = "image"
    THUMBNAIL = "thumbnail"
    OCR = "ocr"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    MANIFEST = "manifest"
    STRUCTURAL = "structural"
    FULL = "full"
    OTHER = "other"


class ProviderRole(Enum):
    """Role of a provider in the data supply chain."""

    DATA_PROVIDER = "data_provider"
    INTERMEDIATE = "intermediate"
    AGGREGATOR = "aggregator"


@dataclass
class Resource:
    """A downloadable file attached to an Item (Schema.org MediaObject)."""

    url: str
    role: ResourceRole
    mime_type: str | None = None
    local_path: Path | None = None
    fallback_url: str | None = None
    service_url: str | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    size_bytes: int | None = None


@dataclass
class Provider:
    """A data provider in the provenance chain (EDM ore:Aggregation)."""

    name: str
    url: str | None = None
    role: ProviderRole = ProviderRole.DATA_PROVIDER


@dataclass
class Metadata:
    """Structured metadata for a cultural heritage item.

    Explicit Dublin Core fields plus an ``extra`` dict for anything else.
    """

    title: str | None = None
    creator: str | None = None
    date: str | None = None
    language: str | None = None
    source_url: str | None = None
    license: str | None = None
    rights: str | None = None
    description: str | None = None
    contributor: str | None = None
    publisher: str | None = None
    type: str | None = None
    format: str | None = None
    identifier: str | None = None
    subject: list[str] = field(default_factory=list)
    relation: str | None = None
    coverage: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Item:
    """A universal node in the cultural heritage hierarchy.

    Everything is an Item — a work, edition, volume, page, image, audio track.
    The ``work_type`` enum says what kind. ``children`` form a tree.
    ``position`` is machine-readable order; ``label`` is the human display string.
    """

    item_id: str
    work_type: WorkType
    source_url: str | None = None
    position: int | None = None
    label: str | None = None
    metadata: Metadata = field(default_factory=Metadata)
    text: str | None = None
    resources: list[Resource] = field(default_factory=list)
    children: list[Item] = field(default_factory=list)
    parent: Item | None = field(default=None, repr=False)
    data_provider: Provider | None = None
    intermediate_provider: Provider | None = None
    aggregator: Provider | None = None
    local_dir: Path | None = None

    def add_child(self, child: Item) -> None:
        """Append a child item and set its parent back-reference."""
        child.parent = self
        self.children.append(child)

    def get_children_by_type(self, work_type: WorkType) -> list[Item]:
        """Return direct children matching the given work type."""
        return [c for c in self.children if c.work_type == work_type]

    def get_resources_by_role(self, role: ResourceRole) -> list[Resource]:
        """Return resources on this item matching the given role."""
        return [r for r in self.resources if r.role == role]

    @property
    def all_resources(self) -> list[Resource]:
        """Recursively collect all resources from this item and descendants."""
        result = list(self.resources)
        for child in self.children:
            result.extend(child.all_resources)
        return result

    @property
    def all_descendants(self) -> list[Item]:
        """Recursively flatten all descendant items."""
        result: list[Item] = []
        for child in self.children:
            result.append(child)
            result.extend(child.all_descendants)
        return result


@dataclass
class Record:
    """Pipeline envelope wrapping an Item as it flows through stages."""

    id: str
    source: str
    stage: PipelineStage = PipelineStage.DISCOVERED
    item: Item | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineContext:
    """Runtime context passed through pipeline stages."""

    adapter_name: str
    output_dir: Path
    state_dir: Path
    config: dict[str, Any] = field(default_factory=dict)

"""FineCurator: A modular toolkit for curating cultural heritage datasets."""

from finecurator.adapters.base import BaseAdapter
from finecurator.models import (
    Item,
    Metadata,
    PipelineContext,
    PipelineStage,
    Provider,
    ProviderRole,
    Record,
    Resource,
    ResourceRole,
    WorkType,
)
from finecurator.pipeline import Pipeline
from finecurator.registry import get_adapter, list_adapters

__all__ = [
    "BaseAdapter",
    "Item",
    "Metadata",
    "Pipeline",
    "PipelineContext",
    "PipelineStage",
    "Provider",
    "ProviderRole",
    "Record",
    "Resource",
    "ResourceRole",
    "WorkType",
    "get_adapter",
    "list_adapters",
]

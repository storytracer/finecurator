"""FineCurator: A modular toolkit for curating cultural heritage datasets."""

from finecurator.adapters.base import BaseAdapter
from finecurator.models import Metadata, PipelineContext, PipelineStage, Record
from finecurator.pipeline import Pipeline
from finecurator.registry import get_adapter, list_adapters

__all__ = [
    "BaseAdapter",
    "Metadata",
    "Pipeline",
    "PipelineContext",
    "PipelineStage",
    "Record",
    "get_adapter",
    "list_adapters",
]

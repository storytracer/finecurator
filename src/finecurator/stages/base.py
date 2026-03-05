"""Abstract base class for pipeline stages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterable, AsyncIterator
from typing import ClassVar

from finecurator.models import PipelineContext, Record


class BaseStage(ABC):
    """Contract for a single pipeline stage.

    Each stage receives an async iterable of records, processes them,
    and yields updated records.
    """

    name: ClassVar[str]

    @abstractmethod
    async def run(
        self,
        records: AsyncIterable[Record],
        context: PipelineContext,
    ) -> AsyncIterator[Record]:
        """Run this stage over the given records."""
        ...

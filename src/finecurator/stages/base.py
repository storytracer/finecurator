"""Abstract base class for pipeline stages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from typing import ClassVar

from finecurator.models import PipelineContext, Record


class BaseStage(ABC):
    """Contract for a single pipeline stage.

    Each stage receives an iterable of records, processes them, and
    yields updated records.  Stages are independently runnable and
    resumable.
    """

    name: ClassVar[str]

    @abstractmethod
    def run(
        self,
        records: Iterable[Record],
        context: PipelineContext,
    ) -> Iterator[Record]:
        """Run this stage over the given records.

        Args:
            records: Input records from the previous stage.
            context: Pipeline runtime context.

        Yields:
            Updated records after this stage's processing.
        """
        ...

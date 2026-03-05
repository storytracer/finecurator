"""Abstract base classes for metadata format parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")  # Input type
R = TypeVar("R")  # Result type


class MetadataParser(ABC, Generic[T, R]):
    """Abstract base class for metadata format parsers."""

    @abstractmethod
    def parse(self, data: T) -> R:
        ...

    @abstractmethod
    def validate(self, data: T) -> bool:
        ...

    @property
    @abstractmethod
    def format_name(self) -> str:
        ...

    @property
    @abstractmethod
    def mime_types(self) -> list[str]:
        ...


class VersionedParser(MetadataParser[T, R]):
    """Base class for parsers that handle multiple format versions."""

    @abstractmethod
    def detect_version(self, data: T) -> str | None:
        ...

    @abstractmethod
    def supported_versions(self) -> list[str]:
        ...

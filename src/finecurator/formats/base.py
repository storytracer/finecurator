"""Abstract base classes for metadata format parsers and writers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
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


class MetadataWriter(ABC, Generic[T]):
    """Abstract base class for metadata format writers."""

    @abstractmethod
    def write(self, data: T, output_path: Path, **options) -> None:
        ...

    @abstractmethod
    def to_string(self, data: T, **options) -> str:
        ...

    @abstractmethod
    def validate_output(self, data: T) -> bool:
        ...

    @property
    @abstractmethod
    def format_name(self) -> str:
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        ...


class VersionedParser(MetadataParser[T, R]):
    """Base class for parsers that handle multiple format versions."""

    @abstractmethod
    def detect_version(self, data: T) -> str | None:
        ...

    @abstractmethod
    def supported_versions(self) -> list[str]:
        ...

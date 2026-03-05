"""IIIF Presentation API manifest parser (v2 and v3).

Parses manifests into format-specific dataclasses. Conversion to
Item/Resource trees happens in the protocol layer (protocols/iiif.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finecurator.formats.base import VersionedParser


# ── Format-specific dataclasses ──────────────────────────────────────


@dataclass
class IIIFService:
    """IIIF Image Service information."""

    id: str
    type: str | None = None
    profile: str | None = None
    context: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IIIFService:
        return cls(
            id=data.get("@id") or data.get("id", ""),
            type=data.get("@type") or data.get("type"),
            profile=data.get("profile"),
            context=data.get("@context") or data.get("context"),
        )


@dataclass
class IIIFImage:
    """IIIF Image resource."""

    id: str
    type: str | None = None
    format: str | None = None
    width: int | None = None
    height: int | None = None
    service: IIIFService | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IIIFImage:
        service_data = data.get("service")
        service = None
        if service_data:
            if isinstance(service_data, list) and service_data:
                service = IIIFService.from_dict(service_data[0])
            elif isinstance(service_data, dict):
                service = IIIFService.from_dict(service_data)

        return cls(
            id=data.get("@id") or data.get("id", ""),
            type=data.get("@type") or data.get("type"),
            format=data.get("format"),
            width=data.get("width"),
            height=data.get("height"),
            service=service,
        )


@dataclass
class IIIFCanvas:
    """IIIF Canvas (page) information."""

    id: str
    label: str | None = None
    width: int | None = None
    height: int | None = None
    images: list[IIIFImage] = field(default_factory=list)

    @classmethod
    def from_dict_v2(cls, data: dict[str, Any]) -> IIIFCanvas:
        images = []
        for img_data in data.get("images", []):
            resource = img_data.get("resource", {})
            if resource:
                images.append(IIIFImage.from_dict(resource))

        return cls(
            id=data.get("@id", ""),
            label=data.get("label", ""),
            width=data.get("width"),
            height=data.get("height"),
            images=images,
        )

    @classmethod
    def from_dict_v3(cls, data: dict[str, Any]) -> IIIFCanvas:
        images = []
        for item in data.get("items", []):
            for annotation in item.get("items", []):
                body = annotation.get("body", {})
                if body:
                    images.append(IIIFImage.from_dict(body))

        label_raw = data.get("label", "")
        if isinstance(label_raw, dict):
            for vals in label_raw.values():
                if vals:
                    label = vals[0]
                    break
            else:
                label = ""
        else:
            label = label_raw

        return cls(
            id=data.get("id", ""),
            label=label,
            width=data.get("width"),
            height=data.get("height"),
            images=images,
        )


@dataclass
class IIIFManifestV2:
    """IIIF Presentation API v2 Manifest."""

    id: str
    label: str | None = None
    description: str | None = None
    metadata: list[dict[str, Any]] = field(default_factory=list)
    canvases: list[IIIFCanvas] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IIIFManifestV2:
        canvases = []
        for sequence in data.get("sequences", []):
            for canvas_data in sequence.get("canvases", []):
                canvases.append(IIIFCanvas.from_dict_v2(canvas_data))

        return cls(
            id=data.get("@id", ""),
            label=data.get("label", ""),
            description=data.get("description", ""),
            metadata=data.get("metadata", []),
            canvases=canvases,
        )


@dataclass
class IIIFManifestV3:
    """IIIF Presentation API v3 Manifest."""

    id: str
    type: str = ""
    label: dict[str, list[str]] | None = None
    summary: dict[str, list[str]] | None = None
    metadata: list[dict[str, Any]] = field(default_factory=list)
    items: list[IIIFCanvas] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IIIFManifestV3:
        items = []
        for canvas_data in data.get("items", []):
            items.append(IIIFCanvas.from_dict_v3(canvas_data))

        return cls(
            id=data.get("id", ""),
            type=data.get("type", ""),
            label=data.get("label"),
            summary=data.get("summary"),
            metadata=data.get("metadata", []),
            items=items,
        )

    @property
    def canvases(self) -> list[IIIFCanvas]:
        return self.items


# ── Parser ───────────────────────────────────────────────────────────


class IIIFParser(VersionedParser[dict[str, Any], IIIFManifestV2 | IIIFManifestV3]):
    """Parser for IIIF Presentation API manifests (v2 and v3).

    Auto-detects the version and returns the appropriate data model.
    """

    def parse(self, data: dict[str, Any]) -> IIIFManifestV2 | IIIFManifestV3:
        if "type" in data and data.get("type") == "Manifest":
            return IIIFManifestV3.from_dict(data)
        elif "@context" in data or "sequences" in data:
            return IIIFManifestV2.from_dict(data)
        else:
            raise ValueError("Unable to determine IIIF manifest version")

    def validate(self, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        version = self.detect_version(data)
        if version == "3.0":
            return ("@context" in data or "context" in data) and "id" in data and data.get("type") == "Manifest"
        elif version == "2.1":
            return ("@context" in data or "context" in data) and ("@id" in data or "id" in data)
        return False

    def detect_version(self, data: dict[str, Any]) -> str | None:
        if not isinstance(data, dict):
            return None
        if "type" in data and data.get("type") == "Manifest":
            return "3.0"
        if "@context" in data or "sequences" in data:
            context = data.get("@context", "")
            if isinstance(context, str):
                if "presentation/3" in context:
                    return "3.0"
            return "2.1"
        return None

    def supported_versions(self) -> list[str]:
        return ["2.1", "3.0"]

    @property
    def format_name(self) -> str:
        return "IIIF Presentation API"

    @property
    def mime_types(self) -> list[str]:
        return ["application/json", "application/ld+json", "application/iiif+json"]


def parse_iiif_manifest(data: dict[str, Any]) -> IIIFManifestV2 | IIIFManifestV3:
    """Convenience function: parse IIIF manifest with auto version detection."""
    return IIIFParser().parse(data)

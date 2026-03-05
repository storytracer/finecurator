"""ALTO (Analyzed Layout and Text Object) format parser.

Supports ALTO versions 1-4 with automatic version detection.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from finecurator.formats.base import VersionedParser


class ALTOString(BaseModel):
    content: str
    confidence: float | None = None
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None


class ALTOTextLine(BaseModel):
    strings: list[ALTOString] = Field(default_factory=list)
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None

    def get_text(self) -> str:
        return " ".join(s.content for s in self.strings)


class ALTOTextBlock(BaseModel):
    lines: list[ALTOTextLine] = Field(default_factory=list)
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None

    def get_text(self) -> str:
        return "\n".join(line.get_text() for line in self.lines)


class ALTOPage(BaseModel):
    width: int
    height: int
    blocks: list[ALTOTextBlock] = Field(default_factory=list)
    physical_img_nr: int | None = None
    page_id: str | None = None

    def get_text(self) -> str:
        return "\n\n".join(block.get_text() for block in self.blocks)


class ALTODocument(BaseModel):
    version: str | None = None
    page: ALTOPage | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_text(self) -> str:
        return self.page.get_text() if self.page else ""


class ALTOParser(VersionedParser[str, ALTODocument]):
    """Parser for ALTO XML documents (versions 1-4)."""

    def parse(self, data: str) -> ALTODocument:
        try:
            root = ET.fromstring(data)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}") from e

        version = self.detect_version(data)
        namespace = self._get_namespace(root)

        layout = root.find(f".//{{{namespace}}}Layout") if namespace else root.find(".//Layout")
        if layout is None:
            raise ValueError("No Layout section found in ALTO document")

        page = self._parse_page(layout, namespace)
        metadata = self._parse_metadata(root, namespace)

        return ALTODocument(version=version, page=page, metadata=metadata)

    def validate(self, data: str) -> bool:
        try:
            root = ET.fromstring(data)
            namespace = self._get_namespace(root)
            if not namespace or "alto" not in namespace.lower():
                return False
            return root.find(f".//{{{namespace}}}Layout") is not None
        except Exception:
            return False

    def detect_version(self, data: str) -> str | None:
        try:
            root = ET.fromstring(data)
            namespace = self._get_namespace(root)
            if not namespace:
                return None
            if "ns-v4" in namespace:
                return "4.0"
            elif "ns-v3" in namespace:
                return "3.0"
            elif "ns-v2" in namespace:
                return "2.0"
            elif "ns-v1" in namespace:
                return "1.0"
            return None
        except Exception:
            return None

    def supported_versions(self) -> list[str]:
        return ["1.0", "2.0", "3.0", "4.0"]

    @property
    def format_name(self) -> str:
        return "ALTO"

    @property
    def mime_types(self) -> list[str]:
        return ["application/xml", "text/xml", "application/alto+xml"]

    def extract_text_only(self, data: str) -> str:
        """Extract plain text from ALTO XML without full structure parsing."""
        try:
            root = ET.fromstring(data)
            namespace = self._get_namespace(root)
            strings = []
            tag = f".//{{{namespace}}}String" if namespace else ".//String"
            for string_elem in root.findall(tag):
                content = string_elem.get("CONTENT")
                if content:
                    strings.append(content)
            return " ".join(strings)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}") from e

    def _get_namespace(self, root: ET.Element) -> str | None:
        tag = root.tag
        if tag.startswith("{"):
            return tag[1 : tag.index("}")]
        return None

    def _parse_page(self, layout: ET.Element, namespace: str | None) -> ALTOPage:
        tag = f"{{{namespace}}}Page" if namespace else "Page"
        page_elem = layout.find(tag)
        if page_elem is None:
            raise ValueError("No Page element found in Layout")

        width = int(page_elem.get("WIDTH", "0"))
        height = int(page_elem.get("HEIGHT", "0"))

        ps_tag = f"{{{namespace}}}PrintSpace" if namespace else "PrintSpace"
        print_space = page_elem.find(ps_tag)
        blocks = []
        if print_space is not None:
            tb_tag = f"{{{namespace}}}TextBlock" if namespace else "TextBlock"
            for tb in print_space.findall(tb_tag):
                blocks.append(self._parse_text_block(tb, namespace))

        return ALTOPage(
            width=width,
            height=height,
            blocks=blocks,
            physical_img_nr=int(v) if (v := page_elem.get("PHYSICAL_IMG_NR")) else None,
            page_id=page_elem.get("ID"),
        )

    def _parse_text_block(self, elem: ET.Element, namespace: str | None) -> ALTOTextBlock:
        tl_tag = f"{{{namespace}}}TextLine" if namespace else "TextLine"
        lines = [self._parse_text_line(tl, namespace) for tl in elem.findall(tl_tag)]
        return ALTOTextBlock(
            lines=lines,
            x=int(elem.get("HPOS", "0")),
            y=int(elem.get("VPOS", "0")),
            width=int(elem.get("WIDTH", "0")),
            height=int(elem.get("HEIGHT", "0")),
        )

    def _parse_text_line(self, elem: ET.Element, namespace: str | None) -> ALTOTextLine:
        s_tag = f"{{{namespace}}}String" if namespace else "String"
        strings = []
        for s in elem.findall(s_tag):
            wc = s.get("WC")
            strings.append(
                ALTOString(
                    content=s.get("CONTENT", ""),
                    confidence=float(wc) if wc else None,
                    x=int(s.get("HPOS", "0")),
                    y=int(s.get("VPOS", "0")),
                    width=int(s.get("WIDTH", "0")),
                    height=int(s.get("HEIGHT", "0")),
                )
            )
        return ALTOTextLine(
            strings=strings,
            x=int(elem.get("HPOS", "0")),
            y=int(elem.get("VPOS", "0")),
            width=int(elem.get("WIDTH", "0")),
            height=int(elem.get("HEIGHT", "0")),
        )

    def _parse_metadata(self, root: ET.Element, namespace: str | None) -> dict:
        metadata: dict = {}
        desc_tag = f"{{{namespace}}}Description" if namespace else "Description"
        description = root.find(desc_tag)
        if description is not None:
            mu_tag = f"{{{namespace}}}MeasurementUnit" if namespace else "MeasurementUnit"
            mu = description.find(mu_tag)
            if mu is not None and mu.text:
                metadata["measurement_unit"] = mu.text
            ocr_tag = f".//{{{namespace}}}OCRProcessing" if namespace else ".//OCRProcessing"
            ocr = description.find(ocr_tag)
            if ocr is not None:
                ocr_id = ocr.get("ID")
                if ocr_id:
                    metadata["ocr_processing_id"] = ocr_id
        return metadata


def parse_alto_xml(xml_content: str) -> ALTODocument:
    """Convenience: parse ALTO XML into an ALTODocument."""
    return ALTOParser().parse(xml_content)


def extract_text_from_alto(xml_content: str) -> str:
    """Convenience: extract plain text from ALTO XML."""
    return ALTOParser().extract_text_only(xml_content)

"""METS (Metadata Encoding and Transmission Standard) format parser.

Supports MODS metadata extraction and physical structure parsing.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from finecurator.formats.base import MetadataParser

METS_NAMESPACES = {
    "mets": "http://www.loc.gov/METS/",
    "mods": "http://www.loc.gov/mods/v3",
    "xlink": "http://www.w3.org/1999/xlink",
    "oai": "http://www.openarchives.org/OAI/2.0/",
}


class METSFile(BaseModel):
    """A file reference in METS."""

    id: str
    mimetype: str
    href: str
    use: str | None = None


class METSPage(BaseModel):
    """A page in METS physical structure."""

    id: str
    label: str
    order: int
    file_ids: list[str] = Field(default_factory=list)


class METSMetadata(BaseModel):
    """MODS metadata extracted from METS."""

    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    publisher: str | None = None
    date: str | None = None
    language: str | None = None
    extent: str | None = None
    doi: str | None = None
    license: str | None = None


class METSDocument(BaseModel):
    """A parsed METS document."""

    metadata: METSMetadata
    pages: list[METSPage] = Field(default_factory=list)
    files: dict[str, METSFile] = Field(default_factory=dict)


class METSParser(MetadataParser[str, METSDocument]):
    """Parser for METS XML documents.

    Extracts MODS metadata, file references, and physical structure.
    """

    def parse(self, data: str) -> METSDocument:
        try:
            root = ET.fromstring(data)

            oai_record = root.find(
                ".//oai:record/oai:metadata/mets:mets", METS_NAMESPACES
            )
            if oai_record is not None:
                root = oai_record

            metadata = self._parse_mods_metadata(root)
            files = self._parse_file_section(root)
            pages = self._parse_physical_structure(root)

            return METSDocument(metadata=metadata, pages=pages, files=files)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to parse METS: {e}") from e

    def validate(self, data: str) -> bool:
        try:
            root = ET.fromstring(data)
            if "mets" not in root.tag and "METS" not in root.tag:
                oai_record = root.find(
                    ".//oai:record/oai:metadata/mets:mets", METS_NAMESPACES
                )
                if oai_record is None:
                    return False

            for section in ("metsHdr", "fileSec", "structMap"):
                if root.find(f".//mets:{section}", METS_NAMESPACES) is not None:
                    return True
            return False
        except Exception:
            return False

    @property
    def format_name(self) -> str:
        return "METS"

    @property
    def mime_types(self) -> list[str]:
        return ["application/xml", "text/xml", "application/mets+xml"]

    def _parse_mods_metadata(self, root: ET.Element) -> METSMetadata:
        mods = root.find(".//mods:mods", METS_NAMESPACES)
        if mods is None:
            return METSMetadata()

        def _text(xpath: str) -> str | None:
            el = mods.find(xpath, METS_NAMESPACES)
            return el.text.strip() if el is not None and el.text else None

        return METSMetadata(
            title=_text(".//mods:titleInfo/mods:title"),
            subtitle=_text(".//mods:titleInfo/mods:subTitle"),
            author=_text('.//mods:name[@type="personal"]/mods:namePart'),
            publisher=_text(".//mods:originInfo/mods:publisher"),
            date=_text(".//mods:originInfo/mods:dateIssued"),
            language=_text(".//mods:language/mods:languageTerm"),
            extent=_text(".//mods:physicalDescription/mods:extent"),
            doi=_text('.//mods:identifier[@type="doi"]'),
            license=_text(".//mods:accessCondition"),
        )

    def _parse_file_section(self, root: ET.Element) -> dict[str, METSFile]:
        files: dict[str, METSFile] = {}
        file_sec = root.find(".//mets:fileSec", METS_NAMESPACES)
        if file_sec is None:
            return files

        for file_grp in file_sec.findall(".//mets:fileGrp", METS_NAMESPACES):
            use = file_grp.get("USE")
            for file_elem in file_grp.findall(".//mets:file", METS_NAMESPACES):
                file_id = file_elem.get("ID")
                mimetype = file_elem.get("MIMETYPE", "")
                flocat = file_elem.find(".//mets:FLocat", METS_NAMESPACES)
                if flocat is not None and file_id:
                    href = flocat.get("{http://www.w3.org/1999/xlink}href", "")
                    files[file_id] = METSFile(
                        id=file_id, mimetype=mimetype, href=href, use=use
                    )
        return files

    def _parse_physical_structure(self, root: ET.Element) -> list[METSPage]:
        pages: list[METSPage] = []
        phys_struct = root.find(
            './/mets:structMap[@TYPE="PHYSICAL"]', METS_NAMESPACES
        )
        if phys_struct is None:
            return pages

        for div in phys_struct.findall('.//mets:div[@TYPE="page"]', METS_NAMESPACES):
            page_id = div.get("ID", "")
            label = div.get("LABEL", "")
            try:
                order = int(div.get("ORDER", "0"))
            except (ValueError, TypeError):
                order = 0

            file_ids = [
                fptr.get("FILEID")
                for fptr in div.findall(".//mets:fptr", METS_NAMESPACES)
                if fptr.get("FILEID")
            ]

            pages.append(
                METSPage(id=page_id, label=label, order=order, file_ids=file_ids)
            )

        return pages


def parse_mets_xml(xml_content: str) -> METSDocument:
    """Convenience function: parse METS XML into a METSDocument."""
    return METSParser().parse(xml_content)

"""Format parsers for metadata and manifest formats.

- IIIF Presentation API (v2/v3)
- METS (Metadata Encoding and Transmission Standard)
- ALTO (Analyzed Layout and Text Object)
"""

from finecurator.formats.base import MetadataParser, VersionedParser

__all__ = [
    "MetadataParser",
    "VersionedParser",
]

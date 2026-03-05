"""Format parsers and writers for metadata and manifest formats.

- IIIF Presentation API (v2/v3)
- METS (Metadata Encoding and Transmission Standard)
- ALTO (Analyzed Layout and Text Object)
- RO-Crate (Research Object Crate)
"""

from finecurator.formats.base import MetadataParser, MetadataWriter, VersionedParser

__all__ = [
    "MetadataParser",
    "MetadataWriter",
    "VersionedParser",
]

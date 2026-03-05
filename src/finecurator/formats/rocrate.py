"""RO-Crate (Research Object Crate) metadata writer.

Accepts an Item tree and writes RO-Crate metadata conforming to the
RO-Crate 1.1/1.2 specification. Maps Dublin Core metadata to Schema.org.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from rocrate.model.contextentity import ContextEntity
from rocrate.model.person import Person
from rocrate.rocrate import ROCrate

from finecurator.formats.base import MetadataWriter

if TYPE_CHECKING:
    from finecurator.models import Item


# Dublin Core -> Schema.org property mappings
DC_TO_SCHEMA_ORG = {
    "title": "name",
    "creator": "creator",
    "subject": "keywords",
    "description": "description",
    "publisher": "publisher",
    "contributor": "contributor",
    "date": "datePublished",
    "type": "additionalType",
    "format": "encodingFormat",
    "identifier": "identifier",
    "source_url": "isBasedOn",
    "language": "inLanguage",
    "relation": "relatedLink",
    "coverage": "spatialCoverage",
    "rights": "license",
    "license": "license",
}


class ROCrateWriter(MetadataWriter["Item"]):
    """Writer for RO-Crate metadata files from Item trees.

    Walks the Item tree recursively, maps Metadata to Schema.org,
    and maps Provider to RO-Crate entities.
    """

    def __init__(self, include_files: bool = True):
        self.include_files = include_files

    def write(self, data: Item, output_path: Path, **options) -> None:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        crate = self._create_crate(data, output_path)
        crate.metadata.write(output_path)

    def to_string(self, data: Item, **options) -> str:
        crate = self._create_crate(data, None)
        graph = crate.metadata._jsonld.get("@graph", [])
        rocrate_dict = {
            "@context": crate.metadata._jsonld.get("@context"),
            "@graph": graph,
        }
        return json.dumps(rocrate_dict, indent=2, ensure_ascii=False)

    def validate_output(self, data: Item) -> bool:
        from finecurator.models import Item as ItemCls

        if not isinstance(data, ItemCls):
            return False
        md = data.metadata
        return bool(md.title and md.creator and md.date)

    @property
    def format_name(self) -> str:
        return "RO-Crate"

    @property
    def file_extension(self) -> str:
        return ".json"

    def _create_crate(self, item: Item, base_path: Path | None) -> ROCrate:
        crate = ROCrate()
        root = crate.root_dataset
        md = item.metadata

        if md.title:
            root["name"] = md.title
        if md.date:
            root["datePublished"] = md.date

        if md.creator:
            creator = Person(
                crate, identifier=f"#{md.creator.replace(' ', '_')}"
            )
            creator["name"] = md.creator
            crate.add(creator)
            root["creator"] = creator

        if md.contributor:
            contrib = Person(
                crate,
                identifier=f"#{md.contributor.replace(' ', '_')}_contributor",
            )
            contrib["name"] = md.contributor
            crate.add(contrib)
            root["contributor"] = contrib

        if md.publisher:
            pub = ContextEntity(
                crate,
                identifier=f"#{md.publisher.replace(' ', '_')}",
                properties={"@type": "Organization", "name": md.publisher},
            )
            crate.add(pub)
            root["publisher"] = pub

        _set_if(root, "additionalType", md.type)
        _set_if(root, "encodingFormat", md.format)
        _set_if(root, "identifier", md.identifier)
        _set_if(root, "isBasedOn", md.source_url)
        _set_if(root, "inLanguage", md.language)
        _set_if(root, "relatedLink", md.relation)
        _set_if(root, "spatialCoverage", md.coverage)
        _set_if(root, "license", md.rights or md.license)
        _set_if(root, "description", md.description)

        if md.subject:
            root["keywords"] = md.subject

        root["workType"] = item.work_type.value
        root["itemId"] = item.item_id

        # Provider entities
        for provider in (item.data_provider, item.intermediate_provider, item.aggregator):
            if provider:
                prov_entity = ContextEntity(
                    crate,
                    identifier=f"#{provider.name.replace(' ', '_')}",
                    properties={
                        "@type": "Organization",
                        "name": provider.name,
                        "role": provider.role.value,
                    },
                )
                if provider.url:
                    prov_entity["url"] = provider.url
                crate.add(prov_entity)

        # hasPart for files
        if self.include_files and base_path:
            parts = self._collect_file_parts(item, base_path)
            if parts:
                root["hasPart"] = [{"@id": p} for p in parts]

        return crate

    def _collect_file_parts(self, item: Item, base_path: Path) -> list[str]:
        parts: list[str] = []
        for resource in item.all_resources:
            if resource.local_path and resource.local_path.exists():
                try:
                    rel_path = resource.local_path.relative_to(base_path)
                    parts.append(str(rel_path))
                except ValueError:
                    parts.append(str(resource.local_path))
        return sorted(parts)


def _set_if(root, key: str, value) -> None:
    if value:
        root[key] = value

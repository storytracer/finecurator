"""Persistent state management for pipeline records."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from finecurator.models import CreativeWork, PipelineStage, Record, stage_gte

logger = logging.getLogger(__name__)


def _rebuild_back_refs(work: CreativeWork) -> None:
    """Reconstruct is_part_of back-references after deserialization."""
    for part in work.parts:
        part.is_part_of = work
        _rebuild_back_refs(part)


class StateManager:
    """Persist and load Record state as JSON files.

    Layout::

        state_dir/
            _sources.json          # {source_url: record_id}
            {record_id}.json       # serialized Record
    """

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    # ── save / load ──────────────────────────────────────────────────

    def save(self, record: Record) -> None:
        path = self.state_dir / f"{record.id}.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        logger.debug("Saved state for %s (stage=%s)", record.id, record.stage.value)

    def load(self, record_id: str) -> Record | None:
        path = self.state_dir / f"{record_id}.json"
        if not path.exists():
            return None
        record = Record.model_validate_json(path.read_text(encoding="utf-8"))
        if record.work:
            _rebuild_back_refs(record.work)
        return record

    # ── stage queries ────────────────────────────────────────────────

    def has_stage(self, record_id: str, stage: PipelineStage) -> bool:
        record = self.load(record_id)
        if record is None:
            return False
        return stage_gte(record.stage, stage)

    def load_at_stage(self, record_id: str, required_stage: PipelineStage) -> Record | None:
        record = self.load(record_id)
        if record is None:
            return None
        if stage_gte(record.stage, required_stage):
            return record
        return None

    # ── source URL mapping ───────────────────────────────────────────

    def _sources_path(self) -> Path:
        return self.state_dir / "_sources.json"

    def _load_sources(self) -> dict[str, str]:
        path = self._sources_path()
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_sources(self, sources: dict[str, str]) -> None:
        self._sources_path().write_text(
            json.dumps(sources, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get_id_for_source(self, source_url: str) -> str | None:
        return self._load_sources().get(source_url)

    def map_source(self, source_url: str, record_id: str) -> None:
        sources = self._load_sources()
        sources[source_url] = record_id
        self._save_sources(sources)

    # ── listing ──────────────────────────────────────────────────────

    def list_records(self) -> list[str]:
        return sorted(
            p.stem for p in self.state_dir.glob("*.json") if p.stem != "_sources"
        )

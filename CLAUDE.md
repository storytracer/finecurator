# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FineCurator is a modular Python toolkit for downloading, processing, and curating datasets from cultural heritage sources (GLAM sector). It serves as the data pipeline behind FineBooks. It functions both as a library and a CLI tool. Successor to pybookget.

## Commands

```bash
# Install dependencies (requires Python 3.12+, uses uv)
uv sync

# Run CLI
uv run finecurator <command>

# Example CLI commands
uv run finecurator adapters                                        # List registered adapters (iiif-generic, erara)
uv run finecurator run iiif-generic --url <manifest_url> -o ./out
uv run finecurator run erara --url <erara_url> -o ./out
uv run finecurator discover iiif-generic --url <manifest_url>
uv run finecurator download iiif-generic --url <manifest_url> -o ./out
uv run finecurator -v run iiif-generic --url <url> -o ./out        # Verbose logging
```

No test suite exists yet. No linter/formatter is configured in pyproject.toml.

## Architecture

### Data Model (`models.py`)

Single unified `Item` class with a `work_type` enum (WorkType) and `parent`/`children` hierarchy. Everything is an Item — a work, edition, volume, page, image, audio track.

- **Item** — Universal node: `item_id`, `work_type`, `position`, `label`, `metadata`, `text`, `resources`, `children`, `parent`, providers, `local_dir`. Helper methods: `add_child()`, `get_children_by_type()`, `get_resources_by_role()`, `all_resources` (recursive), `all_descendants` (recursive).
- **WorkType** enum: WORK, SERIES, COLLECTION, VOLUME, ISSUE, EDITION, DOCUMENT, PART, PAGE, IMAGE, AUDIO, VIDEO, OTHER.
- **Resource** — Downloadable file: `url`, `role` (ResourceRole), `mime_type`, `local_path`, `fallback_url`, `service_url`, dimensions.
- **ResourceRole** enum: IMAGE, THUMBNAIL, OCR, TEXT, AUDIO, VIDEO, MANIFEST, STRUCTURAL, FULL, OTHER.
- **Provider** — Data provenance: `name`, `url`, `role` (ProviderRole: DATA_PROVIDER, INTERMEDIATE, AGGREGATOR).
- **Metadata** — Dublin Core fields: `title`, `creator`, `date`, `language`, `source_url`, `license`, `rights`, `description`, `contributor`, `publisher`, `type`, `format`, `identifier`, `subject`, `relation`, `coverage`, `extra`.
- **Record** — Pipeline envelope: `id`, `source`, `stage` (PipelineStage), `item: Item | None`, `errors`.
- **PipelineContext** — Runtime context: `adapter_name`, `output_dir`, `state_dir`, `config`.

### Pipeline (`pipeline.py`)

Orchestrates six async stages: discover → download → process → clean → validate → output. All stages use `AsyncIterator[Record]`. Clean, validate, and output are placeholders.

### Adapters (`adapters/`)

- **BaseAdapter** (`adapters/base.py`) — Abstract base with async methods. Auto-registers via `__init_subclass__`.
- **IIIFAdapter** (`adapters/iiif.py`, `name="iiif-generic"`) — Generic IIIF manifest adapter. Delegates to `IIIFClient` protocol.
- **ERaraAdapter** (`adapters/erara.py`, `name="erara"`) — e-rara.ch adapter combining IIIF images + METS metadata + ALTO OCR.

### HTTP (`http/`)

- **HttpConfig** (`http/client.py`) — Configuration dataclass for HTTP client (timeout, retries, user agent, IIIF params, etc.).
- **create_client()** — Creates `httpx.AsyncClient` with fake user agent, cookies, headers.
- **download_file()** — Async download with tenacity retry, file-level skip.
- **DownloadManager** (`http/download.py`) — Concurrent downloads with `asyncio.Semaphore`, tqdm progress, fallback URL support.
- **cookies.py** / **headers.py** — Netscape cookie file and header file parsers.

### Formats (`formats/`)

Pure parsers producing format-specific dataclasses. No I/O — conversion to Item/Resource happens in protocols.

- **IIIFParser** (`formats/iiif.py`) — Parses IIIF v2/v3 manifests → `IIIFManifestV2`/`IIIFManifestV3` with canvases and images.
- **METSParser** (`formats/mets.py`) — Parses METS XML → `METSDocument` with MODS metadata, pages, files.
- **ALTOParser** (`formats/alto.py`) — Parses ALTO XML v1-4 → `ALTODocument` with text blocks, lines, strings.
- **ROCrateWriter** (`formats/rocrate.py`) — Writes RO-Crate metadata from Item trees, maps Dublin Core → Schema.org.

### Protocols (`protocols/`)

Own the conversion from format models to Item trees.

- **IIIFClient** (`protocols/iiif.py`) — Fetches IIIF manifests, creates `Item(DOCUMENT)` with `Item(PAGE)` children, each having `Resource(IMAGE)`.
- **OAIPMHClient** (`protocols/oai_pmh.py`) — Stub, raises `NotImplementedError`.

### Utilities (`utils/`)

- **text.py** — URL parsing (`get_domain`, `url_to_slug`, `slug_to_url`, `extract_id_from_url`).
- **file.py** — File operations (`ensure_dir`, `get_file_extension`, `generate_filename`).
- **processing.py** — OCR/HTR/image stubs (raise `NotImplementedError`).
- **cleaning.py** — Text normalization stubs.
- **metadata.py** — Metadata merge/normalization stubs.
- **validation.py** — Quality validation stubs.

### Registry (`registry.py`)

Global dict mapping adapter names to classes. Auto-populated by adapter `__init_subclass__`.

## Key Patterns

- **Single Item class**: Everything is an `Item` with `work_type` enum. Trees via `children`/`parent`. `position` (int) for order, `label` (str) for display.
- **Adapters auto-register**: Subclass `BaseAdapter` with a `name`, implement async abstract methods.
- **All I/O is async**: Pipeline, adapters, protocols use `async/await` and `AsyncIterator`.
- **Format ↔ Protocol separation**: Parsers produce format-specific dataclasses. Protocol clients convert those to Item trees.
- **Resource model**: Files are `Resource` objects with `url`, `role`, `local_path`. `DownloadManager` updates `local_path` on success.
- **CLI uses asyncio.run()**: Click commands wrap async functions.
- **Schema.org-aligned but not dependent**: Field names follow Dublin Core/Schema.org conventions. `ROCrateWriter` serializes to JSON-LD.

## Dependencies

`click`, `httpx[http2]`, `tenacity`, `tqdm`, `fake-useragent`, `rocrate`, `tldextract`, `url64`.

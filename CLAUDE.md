# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FineCurator is a modular Python toolkit for downloading, processing, and curating datasets from cultural heritage repositories (GLAM sector). It serves as the data pipeline behind FineBooks. It functions both as a library and a CLI tool. Successor to pybookget.

## Commands

```bash
# Install dependencies (requires Python 3.12+, uses uv)
uv sync

# Run CLI
uv run finecurator <command>

# Example CLI commands
uv run finecurator repos                                    # List registered repos (erara, ...)
uv run finecurator iiif <manifest_url> -o ./out                    # Fetch any IIIF manifest directly
uv run finecurator run erara --url <erara_url> -o ./out            # Run full pipeline for a repo
uv run finecurator discover erara --url <erara_url>
uv run finecurator download erara --url <erara_url> -o ./out
uv run finecurator -v run erara --url <url> -o ./out               # Verbose logging
```

No test suite exists yet. No linter/formatter is configured in pyproject.toml.

## Architecture

### Data Model (`models.py`)

Built on Schema.org vocabulary. The central class is `CreativeWork` — a universal node that forms trees via `parts`/`is_part_of` (Schema.org `hasPart`/`isPartOf`). `MediaObject` represents downloadable files.

- **CreativeWork** — Universal node using Schema.org types: `id`, `type` (str, e.g. "Book", "Collection", "CreativeWork"), `name`, `url`, `position`, `creator`, `date_published`, `in_language`, `license`, `description`, `publisher`, `contributor`, `identifier`, `keywords`, `text`, `encoding_format`, `parts` (children), `is_part_of` (parent), `associated_media`, `local_dir`, `extra`. Helper methods: `add_part()`, `get_parts_by_type()`, `all_media` (recursive), `all_parts` (recursive).
- **MediaObject** — Downloadable file: `content_url`, `encoding_format`, `width`, `height`, `duration`, `content_size`, `local_path`, `fallback_url`.
- **Record** — Pipeline envelope: `id`, `source`, `stage` (PipelineStage), `work: CreativeWork | None`, `errors`.
- **PipelineContext** — Runtime context: `repo_name`, `output_dir`, `state_dir`, `config`.

### Pipeline (`pipeline.py`)

Orchestrates six async stages: discover -> download -> process -> clean -> validate -> output. All stages use `AsyncIterator[Record]`. Clean, validate, and output are placeholders.

### Repositories (`repos/`)

Each cultural heritage digital repository gets its own module.

- **BaseRepo** (`repos/base.py`) — Abstract base with async methods. Auto-registers via `__init_subclass__`.
- **ERaraRepo** (`repos/erara.py`, `name="erara"`) — e-rara.ch repository combining IIIF images + METS metadata + ALTO OCR.

### HTTP (`http/`)

- **HttpConfig** (`http/client.py`) — Pydantic model for HTTP client configuration (timeout, retries, user agent, IIIF params, etc.).
- **create_client()** — Creates `httpx.AsyncClient` with fake user agent, cookies, headers.
- **download_file()** — Async download with tenacity retry, file-level skip.
- **DownloadManager** (`http/download.py`) — Concurrent downloads with `asyncio.Semaphore`, tqdm progress, fallback URL support.
- **cookies.py** / **headers.py** — Netscape cookie file and header file parsers.

### Formats (`formats/`)

Pure parsers producing format-specific Pydantic models. No I/O — conversion to CreativeWork trees happens in protocols.

- **IIIFParser** (`formats/iiif.py`) — Parses IIIF v2/v3 manifests into `IIIFManifestV2`/`IIIFManifestV3` with canvases and images.
- **METSParser** (`formats/mets.py`) — Parses METS XML into `METSDocument` with MODS metadata, pages, files.
- **ALTOParser** (`formats/alto.py`) — Parses ALTO XML v1-4 into `ALTODocument` with text blocks, lines, strings.

### Protocols (`protocols/`)

Own the conversion from format models to CreativeWork trees.

- **IIIFClient** (`protocols/iiif.py`) — Fetches IIIF manifests, creates `CreativeWork(type="Book")` with page parts, each having image `MediaObject`s. Used directly by the `finecurator iiif` CLI command and composed by repos like ERaraRepo.
- **OAIPMHClient** (`protocols/oai_pmh.py`) — Stub, raises `NotImplementedError`.

### Utilities (`utils/`)

- **text.py** — URL parsing (`get_domain`, `url_to_slug`, `slug_to_url`, `extract_id_from_url`).
- **file.py** — File operations (`ensure_dir`, `get_file_extension`, `generate_filename`).
- **processing.py** — OCR/HTR/image stubs (raise `NotImplementedError`).
- **cleaning.py** — Text normalization stubs.
- **metadata.py** — Metadata merge/normalization stubs.
- **validation.py** — Quality validation stubs.

### Registry (`registry.py`)

Global dict mapping repo names to classes. Auto-populated by repo `__init_subclass__`.

## Key Patterns

- **Schema.org data model**: Everything is a `CreativeWork` with a `type` string (e.g. "Book", "Collection"). Trees via `parts`/`is_part_of`. Files are `MediaObject` with `content_url`, `encoding_format`, `local_path`. Properties use Schema.org naming (`name`, `creator`, `date_published`, `in_language`, etc.).
- **Protocols vs repos**: Protocols (IIIF, OAI-PMH) are *how* you talk to something. Repos (e-rara, Gallica) are *where* you get things — they compose protocols. The `iiif` CLI command uses the IIIF protocol directly; repo commands go through the pipeline.
- **Repos auto-register**: Subclass `BaseRepo` with a `name`, implement async abstract methods.
- **All I/O is async**: Pipeline, repos, protocols use `async/await` and `AsyncIterator`.
- **Pydantic models**: All data models are Pydantic `BaseModel` subclasses, supporting `model_dump()`, `model_dump_json()`, `model_validate()`, `model_validate_json()`. The `is_part_of` back-reference on `CreativeWork` is excluded from serialization to avoid circular references.
- **Format / Protocol separation**: Parsers produce format-specific Pydantic models. Protocol clients convert those to CreativeWork trees.
- **Media model**: Files are `MediaObject` with `content_url`, `encoding_format` (MIME type), `local_path`. `DownloadManager` updates `local_path` on success.
- **CLI uses asyncio.run()**: Click commands wrap async functions.

## Dependencies

`click`, `httpx[http2]`, `pydantic`, `tenacity`, `tqdm`, `fake-useragent`, `tldextract`, `url64`.

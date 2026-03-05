"""Command-line interface for FineCurator."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import click

# Import repos so they auto-register
import finecurator.repos.erara  # noqa: F401
from finecurator.pipeline import Pipeline
from finecurator.protocols.iiif import IIIFClient
from finecurator.registry import list_repos


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging.")
def cli(verbose: bool) -> None:
    """FineCurator: A toolkit for curating cultural heritage datasets."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )


@cli.command("repos")
def list_repos_cmd() -> None:
    """List available repos."""
    names = list_repos()
    if not names:
        click.echo("No repos registered.")
        return
    for name in names:
        click.echo(name)


# ── Direct protocol commands (no repo needed) ───────────────────────


@cli.command()
@click.argument("url")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
def iiif(url: str, output_dir: Path) -> None:
    """Fetch and download a IIIF manifest directly by URL."""

    async def _iiif():
        client = IIIFClient()
        async for work in client.discover(url):
            click.echo(f"[discovered] {work.id}  {work.name}")
            count = await client.download_resources(work, output_dir)
            work.local_dir = output_dir
            click.echo(f"[downloaded] {count} files to {output_dir}")

    asyncio.run(_iiif())


# ── Repo-based pipeline commands ────────────────────────────────────


@cli.command()
@click.argument("repo")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
@click.option("--url", default=None, help="Source URL (manifest, page, etc.).")
@click.option("-f", "--force", is_flag=True, help="Ignore cached state, re-run from scratch.")
@click.option("--export-format", default=None, help="If set, also run export (e.g. png, webp, text).")
def run(repo: str, output_dir: Path, url: str | None, force: bool, export_format: str | None) -> None:
    """Run the pipeline for REPO (discover + download by default)."""
    kwargs: dict = {}
    if url:
        kwargs["url"] = url

    async def _run():
        pipeline = Pipeline(repo_name=repo, output_dir=output_dir)
        records = pipeline.run(force=force, **kwargs)

        if export_format:
            records = pipeline.export(records, export_format=export_format, force=force)

        async for record in records:
            click.echo(f"[{record.stage.value}] {record.id}")
            if record.errors:
                for err in record.errors:
                    click.echo(f"  ERROR: {err}", err=True)

    asyncio.run(_run())


@cli.command()
@click.argument("repo")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
@click.option("--url", default=None, help="Source URL.")
@click.option("-f", "--force", is_flag=True, help="Ignore cached state, re-discover.")
def discover(repo: str, output_dir: Path, url: str | None, force: bool) -> None:
    """Discover records from REPO (saves state for later stages)."""
    kwargs: dict = {}
    if url:
        kwargs["url"] = url

    async def _discover():
        pipeline = Pipeline(repo_name=repo, output_dir=output_dir)
        async for record in pipeline.discover(force=force, **kwargs):
            name = record.work.name if record.work else ""
            click.echo(f"[discovered] {record.id}  {name}")

    asyncio.run(_discover())


@cli.command()
@click.argument("repo")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
@click.option("--url", default=None, help="Source URL.")
@click.option("-f", "--force", is_flag=True, help="Ignore cached state, re-download.")
def download(repo: str, output_dir: Path, url: str | None, force: bool) -> None:
    """Download records from REPO (auto-discovers if needed)."""
    kwargs: dict = {}
    if url:
        kwargs["url"] = url

    async def _download():
        pipeline = Pipeline(repo_name=repo, output_dir=output_dir)
        async for record in pipeline.download(pipeline.discover(force=force, **kwargs), force=force):
            click.echo(f"[downloaded] {record.id}")

    asyncio.run(_download())


@cli.command()
@click.argument("repo")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
@click.option("--url", default=None, help="Source URL.")
@click.option("--export-format", default="png", help="Target format (png, webp, text, etc.).")
@click.option("-f", "--force", is_flag=True, help="Ignore cached state, re-export.")
def export(repo: str, output_dir: Path, url: str | None, export_format: str, force: bool) -> None:
    """Export downloaded files to a target format (auto-downloads if needed)."""
    kwargs: dict = {}
    if url:
        kwargs["url"] = url

    async def _export():
        pipeline = Pipeline(repo_name=repo, output_dir=output_dir)
        records = pipeline.download(pipeline.discover(force=force, **kwargs), force=force)
        async for record in pipeline.export(records, export_format=export_format, force=force):
            click.echo(f"[exported] {record.id} -> {export_format}")
            if record.errors:
                for err in record.errors:
                    click.echo(f"  ERROR: {err}", err=True)

    asyncio.run(_export())

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
from finecurator.registry import get_repo, list_repos


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
def run(repo: str, output_dir: Path, url: str | None) -> None:
    """Run the full pipeline for REPO."""
    kwargs = {}
    if url:
        kwargs["url"] = url

    async def _run():
        pipeline = Pipeline(repo_name=repo, output_dir=output_dir)
        async for record in pipeline.run(**kwargs):
            click.echo(f"[{record.stage.value}] {record.id}")
            if record.errors:
                for err in record.errors:
                    click.echo(f"  ERROR: {err}", err=True)

    asyncio.run(_run())


@cli.command()
@click.argument("repo")
@click.option("--url", default=None, help="Source URL.")
def discover(repo: str, url: str | None) -> None:
    """Discover records from REPO."""
    kwargs = {}
    if url:
        kwargs["url"] = url

    async def _discover():
        repo_inst = get_repo(repo)()
        async for record in repo_inst.discover(**kwargs):
            name = record.work.name if record.work else ""
            click.echo(f"{record.id}  {name}")

    asyncio.run(_discover())


@cli.command()
@click.argument("repo")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
@click.option("--url", default=None, help="Source URL.")
def download(repo: str, output_dir: Path, url: str | None) -> None:
    """Download records from REPO."""
    kwargs = {}
    if url:
        kwargs["url"] = url

    async def _download():
        pipeline = Pipeline(repo_name=repo, output_dir=output_dir)
        async for record in pipeline.download(pipeline.discover(**kwargs)):
            click.echo(f"[downloaded] {record.id}")

    asyncio.run(_download())


@cli.command()
@click.argument("repo")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
@click.option("--url", default=None, help="Source URL.")
def process(repo: str, output_dir: Path, url: str | None) -> None:
    """Process downloaded records from REPO."""
    kwargs = {}
    if url:
        kwargs["url"] = url

    async def _process():
        pipeline = Pipeline(repo_name=repo, output_dir=output_dir)
        records = pipeline.download(pipeline.discover(**kwargs))
        async for record in pipeline.process(records):
            click.echo(f"[processed] {record.id}")

    asyncio.run(_process())


@cli.command()
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
def clean(output_dir: Path) -> None:
    """Clean processed records."""
    click.echo("Clean stage: not yet implemented.")


@cli.command()
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
def validate(output_dir: Path) -> None:
    """Validate cleaned records."""
    click.echo("Validate stage: not yet implemented.")


@cli.command()
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
def output(output_dir: Path) -> None:
    """Output curated dataset."""
    click.echo("Output stage: not yet implemented.")

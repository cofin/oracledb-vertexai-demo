# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Side-effecting registration of every ``coffee`` subcommand.

Importing this module mounts all production-app commands on
``app.cli.main:cli``. Substantial workflows stay in ``app.cli._helpers``;
small command-local helpers live here with their commands.
"""

from __future__ import annotations

from typing import Any, cast

import rich_click as click
from litestar.cli._utils import LitestarEnv
from litestar_granian.cli import run_command as litestar_run_command
from rich import get_console
from rich.prompt import Prompt
from sqlspec.migrations.commands import create_migration_commands

import app.config as app_config
from app.cli._helpers.embeddings import generate_product_embeddings
from app.cli._helpers.fixtures import (
    display_available_tables,
    display_fixture_list,
    display_fixture_results,
    export_fixture_data,
    load_fixture_data,
)
from app.cli.main import cli
from app.cli.utils import async_inject
from app.db.utils import load_fixtures

# Service imports must be runtime (not TYPE_CHECKING) because async_inject calls
# get_type_hints() to resolve dependencies against this module's globals.
from app.domain.products.services import ProductService, VertexAIService  # noqa: TC001
from app.domain.system.services import CacheService  # noqa: TC001
from app.lib.settings import get_settings


async def _clear_application_cache(force: bool, cache_service: CacheService) -> None:
    """Clear application caches."""
    console = get_console()

    if not force:
        console.print("[bold]Tables to clear:[/bold]")
        for table in ("response_cache", "embedding_cache"):
            console.print(f"  • {table}")

        confirm = Prompt.ask(
            "\n[bold red]Are you sure you want to clear these caches?[/bold red]",
            choices=["y", "n"],
            default="n",
        )
        if confirm.lower() != "y":
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

    console.rule("[bold blue]Clearing Caches", style="blue", align="left")
    console.print()
    deleted_count = await cache_service.invalidate_cache()
    console.print(f"[green]✓ Cleared {deleted_count} cache records[/green]")
    console.print()


def _create_run_command() -> click.Command:
    """Build the ``run`` command by copying granian's params and wrapping its callback."""
    original_command = litestar_run_command

    @click.pass_context  # type: ignore[arg-type]
    def wrapped_run(ctx: click.Context, **kwargs: Any) -> None:
        from app.server.asgi import create_app

        env = LitestarEnv.from_env("app.server.asgi:create_app")
        env.app = create_app()
        ctx.obj = env

        if original_command.callback is not None:
            original_command.callback(app=env.app, ctx=ctx, **kwargs)

    new_command = click.command(name="run", help=original_command.help)(wrapped_run)
    new_command.params = original_command.params.copy()
    return new_command


async def _upgrade_database(revision: str, no_fixtures: bool, dry_run: bool) -> None:
    """Upgrade database to a specific revision and optionally load fixtures."""
    console = get_console()
    console.rule("[bold blue]Database Upgrade", style="blue", align="left")
    console.print()
    migration_commands = cast("Any", create_migration_commands(config=app_config.db))
    await migration_commands.upgrade(revision=revision, dry_run=dry_run)

    if dry_run:
        console.print("[yellow]i[/yellow]  Dry run — skipping fixture load")
        return
    if no_fixtures:
        console.print("[yellow]i[/yellow]  Skipping fixture load (--no-fixtures)")
        return

    with console.status("[bold yellow]Loading fixtures...", spinner="dots"):
        results = await load_fixtures(None)
        if not results:
            console.print("[yellow]No fixture files found to load[/yellow]")
        else:
            display_fixture_results(results)
    console.print()


def _show_model_info(vertex_ai_service: VertexAIService) -> None:
    """Show information about currently configured AI models."""
    settings = get_settings()
    console = get_console()
    console.rule("[bold blue]AI Model Configuration", style="blue", align="left")
    console.print()

    console.print(f"[bold]Chat Model:[/bold] {settings.vertex_ai.CHAT_MODEL}")
    console.print(f"[bold]Embedding Model:[/bold] {settings.vertex_ai.EMBEDDING_MODEL}")
    console.print(f"[bold]Google Project:[/bold] {settings.vertex_ai.PROJECT_ID}")
    console.print(f"[bold]Embedding Dimensions:[/bold] {settings.vertex_ai.EMBEDDING_DIMENSIONS}")
    console.print()

    console.print("[bold]🔍 Testing Model Initialization...[/bold]")
    _ = vertex_ai_service.client
    console.print("[bold green]✓ Successfully initialized![/bold green]")
    console.print()


@cli.command(name="bulk-embed", help="Generate or refresh product embeddings with Vertex AI.")
@click.option("--batch-size", default=50, show_default=True, help="Number of products to process per batch.")
@click.option("--force", "-f", is_flag=True, help="Re-embed all products, even when embeddings already exist.")
@async_inject
async def bulk_embed_cmd(
    batch_size: int,
    force: bool,
    product_service: ProductService,
    vertex_ai_service: VertexAIService,
) -> None:
    """Generate document-purpose embeddings for product rows."""
    await generate_product_embeddings(batch_size, force, product_service, vertex_ai_service)


@cli.command(name="clear-cache", help="Clear response and embedding cache tables.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@async_inject
async def clear_cache_cmd(force: bool, cache_service: CacheService) -> None:
    """Clear application caches (response_cache + embedding_cache)."""
    await _clear_application_cache(force, cache_service)


@cli.command(name="model-info", help="Show information about currently configured AI models.")
@async_inject
async def model_info_cmd(vertex_ai_service: VertexAIService) -> None:  # noqa: RUF029
    """Show information about currently configured AI models."""
    _show_model_info(vertex_ai_service)


@cli.command(name="upgrade", help="Upgrade database schema and load fixture data.")
@click.option("--revision", "-r", default="head", show_default=True, help="Target revision")
@click.option("--no-fixtures", is_flag=True, help="Skip fixture loading after migration")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@async_inject
async def upgrade_cmd(
    revision: str,
    no_fixtures: bool,
    dry_run: bool,
) -> None:
    """Upgrade database to a specific revision and optionally load fixtures."""
    await _upgrade_database(revision, no_fixtures, dry_run)


@cli.command(name="load-fixtures", help="Load application fixture data into the database.")
@click.option("--tables", "-t", help="Comma-separated list of specific tables to load (loads all if not specified)")
@click.option("--list", "list_fixtures", is_flag=True, help="List available fixture files")
@async_inject
async def load_fixtures_cmd(tables: str | None, list_fixtures: bool) -> None:
    """Load application fixture data into the database."""
    if list_fixtures:
        display_fixture_list()
        return

    await load_fixture_data(tables)


@cli.command(name="export-fixtures", help="Export coffee data tables to fixture JSON files.")
@click.option("--tables", "-t", help="Comma-separated list of tables to export. Exports all if omitted.")
@click.option("--output-dir", "-o", help="Custom output directory. Defaults to configured fixtures directory.")
@click.option("--no-compress", is_flag=True, help="Export uncompressed JSON. Default is gzipped.")
@click.option("--list", "list_tables", is_flag=True, help="List available tables for export")
@async_inject
async def export_fixtures_cmd(
    tables: str | None,
    output_dir: str | None,
    no_compress: bool,
    list_tables: bool,
) -> None:
    """Export coffee shop fixture tables for committed demo data."""
    if list_tables:
        display_available_tables()
        return

    await export_fixture_data(tables, output_dir, no_compress)


cli.add_command(_create_run_command())

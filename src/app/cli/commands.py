# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Side-effecting registration of every ``coffee`` subcommand.

Importing this module mounts all production-app commands on
``app.cli.main:cli``. Substantial workflows stay in ``app.cli._helpers``;
small command-local helpers live here with their commands. Service imports are
kept at runtime because ``async_inject`` calls ``get_type_hints()`` against
this module's globals.
"""

from __future__ import annotations

import asyncio
import copy
import os
from typing import Any, cast

import rich_click as click
from litestar.cli._utils import LitestarEnv
from litestar_granian.cli import run_command as litestar_run_command
from litestar_queues import QueueService
from litestar_queues._cli import queues_group
from litestar_queues._cli import run_command as queues_run_command
from litestar_queues._cli import run_maintenance_command as queues_maintenance_command
from litestar_queues._cli import run_task_command as queues_run_task_command
from litestar_queues._cli import status_command as queues_status_command
from rich import get_console
from rich.prompt import Prompt
from sqlspec.migrations.commands import create_migration_commands

import app.config as app_config
from app.cli._helpers import configure_apex_cdn_helper
from app.cli._helpers.embeddings import validate_batch_size
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
from app.domain.products.jobs import embed_missing_records
from app.domain.products.services import VertexAIService
from app.domain.system.jobs import cleanup_expired_cache_and_sessions
from app.domain.system.services import CacheService
from app.lib.settings import Settings, get_settings
from app.server.asgi import create_app

_REGISTERED_JOBS = (embed_missing_records, cleanup_expired_cache_and_sessions)


def _bind_litestar_env(ctx: click.Context) -> LitestarEnv:
    """Populate ``ctx.obj`` with a loaded ``LitestarEnv`` for queue/server commands."""
    env = LitestarEnv.from_env("app.server.asgi:create_app")
    env.app = create_app()
    ctx.obj = env
    return env


async def _clear_application_cache(force: bool, cache_service: CacheService) -> None:
    """Clear application caches."""
    console = get_console()

    if not force:
        console.print("[bold]Tables to clear:[/bold]")
        for table in ("response_cache", "embedding_cache"):
            console.print(f"  • {table}")

        confirm = Prompt.ask(
            "\n[bold red]Are you sure you want to clear these caches?[/bold red]", choices=["y", "n"], default="n"
        )
        if confirm.lower() != "y":
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

    console.rule("[bold blue]Clearing Caches", style="blue", align="left")
    console.print()
    expired_count = await cache_service.delete_expired_responses()
    console.print(f"[green]✓ Pruned {expired_count} expired response-cache records[/green]")
    deleted_count = await cache_service.invalidate_cache()
    console.print(f"[green]✓ Cleared {deleted_count} cache records[/green]")
    console.print()


def _create_run_command() -> click.Command:
    """Build the ``run`` command by copying granian's params and wrapping its callback.

    Mutates the copied ``--port`` option default to look up the Cloud Run
    ``PORT`` environment variable before falling back to the standard default,
    and adds ``--no-worker`` to disable the embedded ASGI queue worker when
    running web-only replicas.
    """
    original_command = litestar_run_command

    @click.pass_context
    def wrapped_run(ctx: click.RichContext, /, **kwargs: Any) -> None:
        no_worker = bool(kwargs.pop("no_worker", False))
        if no_worker:
            os.environ["QUEUE_EXECUTION_BACKEND"] = "none"
            Settings.from_env.cache_clear()
            app_config._reset()

        env = _bind_litestar_env(ctx)
        if original_command.callback is not None:
            original_command.callback(app=env.app, ctx=ctx, **kwargs)

    new_command = click.command(name="run", help=original_command.help)(wrapped_run)

    new_params: list[click.Parameter] = []
    for param in original_command.params:
        if isinstance(param, click.Option) and "--port" in param.opts:
            param_copy = copy.copy(param)
            granian_default = param_copy.default
            param_copy.default = lambda _d=granian_default: int(os.getenv("PORT") or _d)
            new_params.append(param_copy)
        else:
            new_params.append(param)
    new_params.append(
        click.Option(
            ["--no-worker"],
            is_flag=True,
            default=False,
            help="Disable the embedded queue worker for this web server invocation.",
        )
    )
    new_command.params = new_params
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

    console.print(f"[bold]Chat Model:[/bold] {settings.ai.chat_model}")
    console.print(f"[bold]Embedding Model:[/bold] {settings.ai.embedding_model}")
    console.print(f"[bold]Google Project:[/bold] {settings.ai.project_id}")
    console.print(f"[bold]Embedding Dimensions:[/bold] {settings.ai.embedding_dimensions}")
    console.print()

    console.print("[bold]🔍 Testing Model Initialization...[/bold]")
    _ = vertex_ai_service.client
    console.print("[bold green]✓ Successfully initialized![/bold green]")
    console.print()


async def _run_bulk_embed(*, batch_size: int, force: bool, queue_service: QueueService) -> None:
    """Enqueue and execute ``products.embed_missing`` in the foreground via ``QueueService``."""
    validate_batch_size(batch_size)
    result = await queue_service.enqueue(
        embed_missing_records, batch_size=batch_size, force=force, execution_backend="immediate"
    )
    await result.refresh()


@cli.command(name="bulk-embed", help="Generate or refresh product embeddings with Vertex AI.")
@click.option("--batch-size", default=50, show_default=True, help="Number of products to process per batch.")
@click.option("--force", "-f", is_flag=True, help="Re-embed all products, even when embeddings already exist.")
@async_inject
async def bulk_embed_cmd(batch_size: int, force: bool, queue_service: QueueService) -> None:
    """Generate document-purpose embeddings through the litestar-queues task pipeline."""
    await _run_bulk_embed(batch_size=batch_size, force=force, queue_service=queue_service)


@cli.command(name="clear-cache", help="Clear response and embedding cache tables.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@async_inject
async def clear_cache_cmd(force: bool, cache_service: CacheService) -> None:
    """Clear application caches (response_cache + embedding_cache)."""
    await _clear_application_cache(force, cache_service)


@cli.command(name="model-info", help="Show information about currently configured AI models.")
@async_inject
async def model_info_cmd(vertex_ai_service: VertexAIService) -> None:
    """Show information about currently configured AI models."""
    await asyncio.sleep(0)
    _show_model_info(vertex_ai_service)


@cli.command(name="upgrade", help="Upgrade database schema and load fixture data.")
@click.option("--revision", "-r", default="head", show_default=True, help="Target revision")
@click.option("--no-fixtures", is_flag=True, help="Skip fixture loading after migration")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@async_inject
async def upgrade_cmd(revision: str, no_fixtures: bool, dry_run: bool) -> None:
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
async def export_fixtures_cmd(tables: str | None, output_dir: str | None, no_compress: bool, list_tables: bool) -> None:
    """Export coffee shop fixture tables for committed demo data."""
    if list_tables:
        display_available_tables()
        return

    await export_fixture_data(tables, output_dir, no_compress)


@cli.command(name="configure-apex-cdn", help="Run APEX CDN configuration against the database as SYSDBA.")
def configure_apex_cmd() -> None:
    """Run APEX CDN configuration against the database as SYSDBA."""
    system_password = os.getenv("DATABASE_SYSTEM_PASSWORD")
    if not system_password:
        msg = "DATABASE_SYSTEM_PASSWORD environment variable is not set"
        raise click.ClickException(msg)

    configure_apex_cdn_helper(system_password)


@cli.group(name="worker", help="Run and inspect Oracle 26ai background queue workers.")
@click.pass_context
def worker_group(ctx: click.RichContext, /) -> None:
    """Bind Litestar application environment for background worker commands."""
    _bind_litestar_env(ctx)


def _register_queue_cli_commands() -> None:
    """Mount ``queues`` and ``worker`` subcommands onto the ``coffee`` CLI group."""

    @click.pass_context
    def _queues_group_callback(ctx: click.RichContext, /) -> None:
        _bind_litestar_env(ctx)

    queues_group.callback = _queues_group_callback
    if queues_group.name not in cli.commands:
        cli.add_command(queues_group)

    for cmd in (queues_run_command, queues_status_command, queues_run_task_command, queues_maintenance_command):
        if cmd.name is not None and cmd.name not in worker_group.commands:
            worker_group.add_command(cmd)


_register_queue_cli_commands()
cli.add_command(_create_run_command())

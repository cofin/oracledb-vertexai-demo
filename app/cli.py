# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line interface."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import click
import structlog
from click import Context
from rich import get_console
from rich.prompt import Prompt

from app.__metadata__ import __version__

if TYPE_CHECKING:
    from rich.console import Console


__all__ = (
    "bulk_embed",
    "clear_cache",
    "dump_data",
    "embed_new",
    "load_fixtures",
    "load_vectors",
    "model_info",
    "truncate_tables",
    "version_callback",
)

logger = structlog.get_logger()


def version_callback(ctx: Context, _: click.Parameter, value: bool) -> None:
    if value and not ctx.resilient_parsing:
        click.echo(f"{__version__}")
        ctx.exit()


# Individual CLI functions - these will be added to Litestar's CLI by the plugin


@click.command()
def load_fixtures() -> None:
    """Load coffee demo fixture data."""
    from app.db.utils import load_database_fixtures

    anyio.run(load_database_fixtures)


@click.command()
def load_vectors() -> None:
    """Generate and load vector embeddings for products."""
    from app.db.utils import _load_vectors

    anyio.run(_load_vectors)


@click.command()
def bulk_embed() -> None:
    """Run bulk embedding job for all products using Vertex AI Batch Prediction."""

    async def _run_bulk_embed() -> None:
        from app.server.deps import provide_product_service
        from app.services.bulk_embedding import BulkEmbeddingService

        console = get_console()
        console.print("[bold cyan]🚀 Starting bulk embedding job...[/bold cyan]")

        products_service = await anext(provide_product_service())
        bulk_service = BulkEmbeddingService(products_service)

        # Run the complete bulk embedding pipeline
        result = await bulk_service.run_bulk_embedding_job()

        if result["status"] == "completed":
            console.print("[bold green]✓ Bulk embedding completed![/bold green]")
            console.print(f"Products exported: {result['products_exported']}")
            console.print(f"Embeddings processed: {result['embeddings_processed']}")
            console.print(f"Job ID: {result['job_id']}")
        elif result["status"] == "skipped":
            console.print(f"[yellow]⚠ {result['reason']}[/yellow]")
        else:
            console.print(f"[bold red]✗ Bulk embedding failed: {result['error']}[/bold red]")

    anyio.run(_run_bulk_embed)


@click.command()
@click.option("--limit", default=200, help="Maximum number of products to process in this batch (default: 200)")
def embed_new(limit: int) -> None:
    """Process new/updated products using online embedding API for real-time updates."""

    async def _embed_new_products() -> None:
        from app.server.deps import provide_product_service
        from app.services.bulk_embedding import OnlineEmbeddingService
        from app.services.vertex_ai import VertexAIService

        console = get_console()
        console.print(f"[bold cyan]🔄 Processing up to {limit} new products...[/bold cyan]")

        products_service = await anext(provide_product_service())
        vertex_ai_service = VertexAIService()
        online_service = OnlineEmbeddingService(vertex_ai_service)

        # Process new products
        processed_count = await online_service.process_new_products(products_service, limit)

        if processed_count > 0:
            console.print(f"[bold green]✓ Processed {processed_count} products![/bold green]")
        else:
            console.print("[yellow]No new products to process[/yellow]")

    anyio.run(_embed_new_products)


@click.command()
def model_info() -> None:
    """Show information about currently configured AI models."""

    def _show_model_info() -> None:
        from app.lib.settings import get_settings
        from app.services.vertex_ai import VertexAIService

        console = get_console()
        console.print("[bold cyan]🤖 AI Model Configuration[/bold cyan]")

        # Show settings
        settings = get_settings()
        console.print(f"[bold]Configured Model:[/bold] {settings.app.GEMINI_MODEL}")
        console.print(f"[bold]Embedding Model:[/bold] {settings.app.EMBEDDING_MODEL}")
        console.print(f"[bold]Google Project:[/bold] {settings.app.GOOGLE_PROJECT_ID}")

        # Test model initialization
        console.print("\n[bold cyan]🔍 Testing Model Initialization...[/bold cyan]")
        try:
            vertex_service = VertexAIService()
            model_info = vertex_service.get_model_info()

            console.print("[bold green]✓ Successfully initialized![/bold green]")
            console.print(f"[bold]Active Model:[/bold] {model_info['active_model']}")

            # Show additional details
            console.print(f"[dim]Full model path: {model_info['active_model_full']}[/dim]")

        except Exception as e:  # noqa: BLE001
            console.print(f"[bold red]✗ Model initialization failed: {e}[/bold red]")

    _show_model_info()


# Functions are exported and added to Litestar CLI by the plugin in server/core.py


@click.command(name="clear-cache")
@click.option(
    "--clear-intent-exemplar",
    is_flag=True,
    help="Also clear intent exemplar cache (WARNING: requires re-computing embeddings)",
)
@click.option(
    "--keep-response-cache",
    is_flag=True,
    help="Keep response cache",
)
@click.option(
    "--keep-embedding-cache",
    is_flag=True,
    help="Keep embedding cache",
)
@click.option(
    "--keep-search-metrics",
    is_flag=True,
    help="Keep search metrics",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clear_cache(
    clear_intent_exemplar: bool,
    keep_response_cache: bool,
    keep_embedding_cache: bool,
    keep_search_metrics: bool,
    force: bool,
) -> None:
    """Clear cache tables in the database.

    By default, clears response_cache, embedding_cache, and search_metrics.
    Intent exemplars are preserved by default to avoid expensive re-computation.
    """
    console = get_console()

    # Determine which tables to clear
    tables_to_clear = []
    if clear_intent_exemplar:
        tables_to_clear.append("intent_exemplar")
    if not keep_response_cache:
        tables_to_clear.append("response_cache")
    if not keep_embedding_cache:
        tables_to_clear.append("embedding_cache")
    if not keep_search_metrics:
        tables_to_clear.append("search_metrics")

    if not tables_to_clear:
        console.print("[yellow]No tables selected for clearing. Use --help to see options.[/yellow]")
        return

    # Show what will be cleared and confirm
    if not force and not _confirm_clear(console, tables_to_clear):
        return

    async def _clear_cache() -> None:
        """Clear cache tables."""
        from app.config import oracle_async

        async with oracle_async.get_connection() as conn:
            cursor = conn.cursor()
            try:
                with console.status("[bold green]Clearing cache tables...") as status:
                    for table_name in tables_to_clear:
                        status.update(f"Clearing {table_name}...")

                        # Validate table name to prevent SQL injection
                        if table_name not in ["intent_exemplar", "response_cache", "search_metrics", "embedding_cache"]:
                            console.print(f"[red]✗ Invalid table name: {table_name}[/red]")
                            continue

                        # Count records first
                        await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608
                        count = (await cursor.fetchone())[0]

                        # Delete all records
                        await cursor.execute(f"DELETE FROM {table_name}")  # noqa: S608
                        await conn.commit()

                        console.print(f"[green]✓ Cleared {count} records from {table_name}[/green]")

                    console.print("\n[bold green]Cache clearing complete![/bold green]")
            finally:
                cursor.close()

    anyio.run(_clear_cache)


def _confirm_clear(console: Console, tables: list[str]) -> bool:
    """Confirm cache clearing with user."""
    console.print("[bold]Tables to clear:[/bold]")
    for table in tables:
        console.print(f"  • {table}")
    confirm = Prompt.ask(
        "\n[bold red]Are you sure you want to clear these tables?[/bold red]",
        choices=["y", "n"],
        default="n",
    )
    if confirm.lower() != "y":
        console.print("[yellow]Operation cancelled.[/yellow]")
        return False
    return True


def _get_tables_to_truncate(skip_cache: bool, skip_session: bool, skip_data: bool) -> list[str]:
    """Get list of tables to truncate based on flags."""
    cache_tables = ["intent_exemplar", "response_cache", "search_metrics", "embedding_cache"]
    session_tables = ["chat_conversation", "user_session"]  # Order matters for FKs
    data_tables = ["inventory", "product", "shop", "company"]  # Order matters for FKs

    tables = []
    if not skip_cache:
        tables.extend(cache_tables)
    if not skip_session:
        tables.extend(session_tables)
    if not skip_data:
        tables.extend(data_tables)
    return tables


def _display_tables(console: Console, tables: list[str]) -> None:
    """Display tables that will be truncated."""
    console.print("[bold]Tables to truncate:[/bold]")
    for table in tables:
        console.print(f"  • {table}")


def _confirm_truncate(console: Console) -> bool:
    """Confirm truncation with user."""
    console.print("\n[bold red]⚠️  WARNING: This will remove ALL data from the selected tables![/bold red]")
    confirm = Prompt.ask(
        "[bold red]Are you absolutely sure?[/bold red]",
        choices=["y", "n"],
        default="n",
    )
    if confirm.lower() != "y":
        console.print("[yellow]Operation cancelled.[/yellow]")
        return False
    return True


@click.command(name="truncate-tables")
@click.option(
    "--skip-cache",
    is_flag=True,
    help="Skip cache tables (intent_exemplar, response_cache, search_metrics)",
)
@click.option(
    "--skip-session",
    is_flag=True,
    help="Skip session tables (user_session, chat_conversation)",
)
@click.option(
    "--skip-data",
    is_flag=True,
    help="Skip data tables (company, shop, product, inventory)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def truncate_tables(
    skip_cache: bool,
    skip_session: bool,
    skip_data: bool,
    force: bool,
) -> None:
    """Truncate all tables in the database (faster than DELETE for resetting data)."""
    console = get_console()

    # Get tables to truncate
    tables = _get_tables_to_truncate(skip_cache, skip_session, skip_data)
    if not tables:
        console.print("[yellow]No tables selected for truncation. Use --help to see options.[/yellow]")
        return

    # Show tables and confirm
    _display_tables(console, tables)
    if not force and not _confirm_truncate(console):
        return

    async def _truncate_tables() -> None:
        """Truncate tables."""
        from app.config import oracle_async

        async with oracle_async.get_connection() as conn:
            cursor = conn.cursor()
            try:
                with console.status("[bold green]Truncating tables...") as status:
                    # Disable FK constraints temporarily for truncation
                    status.update("Disabling foreign key constraints...")

                    # Get all foreign key constraints
                    await cursor.execute("""
                        SELECT constraint_name, table_name
                        FROM user_constraints
                        WHERE constraint_type = 'R'
                        AND status = 'ENABLED'
                    """)
                    constraints = await cursor.fetchall()

                    # Disable constraints
                    for constraint_name, table_name in constraints:
                        await cursor.execute(f"ALTER TABLE {table_name} DISABLE CONSTRAINT {constraint_name}")

                    # Truncate tables
                    for table_name in tables:
                        status.update(f"Truncating {table_name}...")

                        # Validate table name
                        valid_tables = [
                            "intent_exemplar",
                            "response_cache",
                            "search_metrics",
                            "embedding_cache",
                            "chat_conversation",
                            "user_session",
                            "inventory",
                            "product",
                            "shop",
                            "company",
                            "app_config",
                        ]
                        if table_name not in valid_tables:
                            console.print(f"[red]✗ Invalid table name: {table_name}[/red]")
                            continue

                        try:
                            await cursor.execute(f"TRUNCATE TABLE {table_name}")
                            console.print(f"[green]✓ Truncated {table_name}[/green]")
                        except Exception as e:  # noqa: BLE001
                            console.print(f"[red]✗ Failed to truncate {table_name}: {e}[/red]")

                    # Re-enable constraints
                    status.update("Re-enabling foreign key constraints...")
                    for constraint_name, table_name in constraints:
                        await cursor.execute(f"ALTER TABLE {table_name} ENABLE CONSTRAINT {constraint_name}")

                    await conn.commit()
                    console.print("\n[bold green]Table truncation complete![/bold green]")
            finally:
                cursor.close()

    anyio.run(_truncate_tables)


@click.command(name="dump-data")
@click.option(
    "--table",
    "-t",
    default="*",
    help="Table name to export, or '*' for all tables",
)
@click.option(
    "--path",
    "-p",
    default="app/db/fixtures",
    help="Directory to export to",
)
@click.option(
    "--no-compress",
    is_flag=True,
    help="Export uncompressed JSON (default is gzipped)",
)
def dump_data(table: str, path: str, no_compress: bool) -> None:
    """Export database tables to JSON files."""
    from pathlib import Path

    from app.db.utils import dump_database_data

    console = get_console()

    async def _dump_data() -> None:
        """Execute the data dump."""
        export_path = Path(path)
        compress = not no_compress

        # Show what will be exported
        if table == "*":
            console.print("[bold]Exporting all tables...[/bold]")
        else:
            console.print(f"[bold]Exporting table: {table}[/bold]")

        console.print(f"Export path: {export_path}")
        console.print(f"Compression: {'enabled' if compress else 'disabled'}")

        with console.status("[bold green]Exporting data..."):
            results = await dump_database_data(export_path, table, compress)

        # Display results
        console.print("\n[bold]Export Results:[/bold]")
        total_records = 0
        for table_name, count in sorted(results.items()):
            if count >= 0:
                console.print(f"  ✓ {table_name}: {count} records")
                total_records += count
            else:
                console.print(f"  ✗ {table_name}: [red]Failed[/red]")

        console.print(f"\n[bold green]Total records exported: {total_records}[/bold green]")

    anyio.run(_dump_data)


# Main execution removed - CLI is handled by Litestar

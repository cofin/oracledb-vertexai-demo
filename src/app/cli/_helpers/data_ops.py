# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Data operation helpers for ``coffee`` CLI commands."""

from __future__ import annotations

import gzip
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import rich_click as click
import structlog
from rich import get_console
from rich.prompt import Prompt
from rich.table import Table
from sqlspec.migrations.commands import create_migration_commands

import app.config as app_config
from app.db.utils import COFFEE_SHOP_TABLES, export_fixtures, load_fixtures
from app.lib.settings import get_settings
from app.utils.serialization import from_json

if TYPE_CHECKING:
    from sqlspec.migrations.commands import AsyncMigrationCommands

    from app.domain.products.services import ProductService, VertexAIService
    from app.domain.system.services import CacheService

BatchProcessor = Callable[[list[Any], int, int], Awaitable[tuple[int, int]]]

logger = structlog.get_logger()


async def generate_product_embeddings(
    batch_size: int,
    force: bool,
    product_service: ProductService,
    vertex_ai_service: VertexAIService,
) -> None:
    """Generate ``RETRIEVAL_DOCUMENT`` embeddings for product rows."""
    validate_batch_size(batch_size)

    console = get_console()
    console.rule("[bold blue]Product Embeddings", style="blue", align="left")
    console.print()

    products, message = await fetch_products_to_embed(product_service, force)
    console.print(message)

    if not products:
        console.print(
            "[yellow]No products found in database[/yellow]"
            if force
            else "[green]✓ All products already have embeddings![/green]"
        )
        print_embedding_results(0, 0)
        return

    console.print(f"[dim]Batch size: {batch_size}[/dim]\n")
    success, errors = await embed_in_batches(
        products,
        batch_size,
        lambda batch, start_idx, total: process_product_batch(
            batch,
            product_service,
            vertex_ai_service,
            start_idx,
            total,
        ),
    )
    print_embedding_results(success, errors)


async def fetch_products_to_embed(product_service: ProductService, force: bool) -> tuple[list[dict[str, Any]], str]:
    """Fetch products that need embeddings."""
    console = get_console()
    with console.status("[bold yellow]Finding products to process...", spinner="dots"):
        products, _total = await product_service.get_products_for_embedding(force=force)

    label = "ALL products (force mode)" if force else "products without embeddings"
    return products, f"[cyan]Processing {len(products)} {label}[/cyan]"


async def process_product_batch(
    batch: list[Any],
    product_service: ProductService,
    vertex_ai_service: VertexAIService,
    start_idx: int,
    total_products: int,
) -> tuple[int, int]:
    """Process a batch of products for embedding generation."""
    console = get_console()
    success_count = 0
    error_count = 0

    with console.status("[bold yellow]Generating embeddings...", spinner="dots") as status:
        for i, product in enumerate(batch):
            product_id: int | None = None
            try:
                if isinstance(product, dict):
                    product_id = int(product["id"])
                    product_name = product.get("name", f"Product {product_id}")
                    description = product.get("description", "")
                else:
                    product_id = int(product.id)
                    product_name = product.name or f"Product {product_id}"
                    description = product.description or ""

                global_idx = start_idx + i + 1
                status.update(f"[bold yellow]Processing {global_idx}/{total_products}: {product_name}...")

                embedding = await vertex_ai_service.get_text_embedding(
                    f"{product_name}: {description}",
                    task_type="RETRIEVAL_DOCUMENT",
                )
                updated = await product_service.update_embedding(product_id, embedding)
                if not updated:
                    error_count += 1
                    logger.warning("Failed to process product", product_id=product_id, error="update affected 0 rows")
                    continue
                success_count += 1

            except Exception as e:  # noqa: BLE001
                error_count += 1
                logger.warning("Failed to process product", product_id=product_id, error=str(e))

    return success_count, error_count


def validate_batch_size(batch_size: int) -> None:
    """Validate embedding batch size before any service work starts."""
    if batch_size < 1:
        msg = "Batch size must be at least 1."
        raise click.ClickException(msg)


async def embed_in_batches(
    items: list[Any],
    batch_size: int,
    processor: BatchProcessor,
) -> tuple[int, int]:
    """Iterate items in batches and aggregate (success, error) counts."""
    console = get_console()
    total_success = 0
    total_errors = 0
    total_batches = (len(items) + batch_size - 1) // batch_size

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(items))
        batch = items[start_idx:end_idx]
        console.print(f"[bold]Processing batch {batch_num + 1}/{total_batches} ({len(batch)} items)[/bold]")
        success, errors = await processor(batch, start_idx, len(items))
        total_success += success
        total_errors += errors
        console.print(f"[green]✓ Batch {batch_num + 1} complete[/green]\n")

    return total_success, total_errors


def print_embedding_results(total_success: int, total_errors: int) -> None:
    """Print final embedding results."""
    console = get_console()
    console.print("[bold]Results:[/bold]")
    console.print(f"[bold green]✓ Successfully processed: {total_success}[/bold green]")
    if total_errors > 0:
        console.print(f"[bold red]✗ Failed to process: {total_errors}[/bold red]")
    console.print()


async def clear_application_cache(force: bool, cache_service: CacheService) -> None:
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


def show_model_info(vertex_ai_service: VertexAIService) -> None:
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


async def upgrade_database(revision: str, no_fixtures: bool, dry_run: bool) -> None:
    """Upgrade database to a specific revision and optionally load fixtures."""
    console = get_console()
    console.rule("[bold blue]Database Upgrade", style="blue", align="left")
    console.print()

    migration_commands = cast("AsyncMigrationCommands[Any]", create_migration_commands(config=app_config.db))
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


async def downgrade_database(revision: str, dry_run: bool) -> None:
    """Downgrade database to a specific revision."""
    console = get_console()
    console.rule("[bold blue]Database Downgrade", style="blue", align="left")
    console.print()

    migration_commands = cast("AsyncMigrationCommands[Any]", create_migration_commands(config=app_config.db))
    await migration_commands.downgrade(revision=revision, dry_run=dry_run)
    console.print()


def display_fixture_list() -> None:
    """Display available fixture files."""
    console = get_console()
    console.rule("[bold blue]Available Fixture Files", style="blue", align="left")
    console.print()

    fixtures_dir = Path(get_settings().db.FIXTURE_PATH)
    if not fixtures_dir.exists():
        console.print(f"[yellow]Fixtures directory not found: {fixtures_dir}[/yellow]")
        return

    fixture_files = sorted(fixtures_dir.glob("*.json")) + sorted(fixtures_dir.glob("*.json.gz"))
    if not fixture_files:
        console.print("[yellow]No fixture files found in fixtures directory[/yellow]")
        return

    table = Table(show_header=True, header_style="bold blue", expand=True)
    table.add_column("Table", style="cyan", ratio=2)
    table.add_column("File", style="dim", ratio=3)
    table.add_column("Records", justify="right", ratio=1)
    table.add_column("Size", justify="right", ratio=1)
    table.add_column("Status", ratio=2)

    for fixture_file in fixture_files:
        table_name = fixture_file.name.replace(".json.gz", "").replace(".json", "")
        try:
            if fixture_file.suffix == ".gz":
                with gzip.open(fixture_file, "rb") as f:
                    data = from_json(f.read())
            else:
                data = from_json(fixture_file.read_text(encoding="utf-8"))

            records = str(len(data)) if isinstance(data, list) else "1"
            size_bytes = fixture_file.stat().st_size
            size_mb = size_bytes / 1024 / 1024
            size = f"{size_mb:.1f} MB" if size_mb > 1 else f"{size_bytes / 1024:.1f} KB"
            status = "[green]Ready[/green]"
        except (OSError, PermissionError, ValueError) as e:
            records = "[dim]N/A[/dim]"
            size = "[dim]N/A[/dim]"
            status = f"[red]Error: {e}[/red]"

        table.add_row(table_name, fixture_file.name, records, size, status)

    console.print(table)
    console.print()


async def load_fixture_data(tables: str | None) -> None:
    """Load fixture data into database."""
    console = get_console()
    console.rule("[bold blue]Loading Database Fixtures", style="blue", align="left")
    console.print()

    table_list = None
    if tables:
        table_list = [t.strip() for t in tables.split(",")]
        console.print(f"[dim]Loading specific tables: {', '.join(table_list)}[/dim]")
    else:
        console.print("[dim]Loading all available fixtures[/dim]")
    console.print()

    with console.status("[bold yellow]Loading fixtures...", spinner="dots"):
        results = await load_fixtures(table_list)

        if not results:
            console.print("[yellow]No fixture files found to load[/yellow]")
            return

        display_fixture_results(results)


def display_fixture_results(results: dict[str, Any]) -> None:
    """Display fixture loading results."""
    console = get_console()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Table", style="cyan", width=35)
    table.add_column("Status", width=100)

    total_upserted = 0
    total_failed = 0
    total_records = 0

    for table_name, result in results.items():
        row_data = process_fixture_result(table_name, result)
        table.add_row(row_data["row"][0], row_data["row"][4])

        total_upserted += row_data["upserted"]
        total_failed += row_data["failed"]
        total_records += row_data["total"]

    console.print(table)
    console.print()
    print_fixture_summary(total_upserted, total_failed, total_records)


def process_fixture_result(table_name: str, result: dict[str, Any] | str) -> dict[str, Any]:
    """Format a single fixture result row for the summary table."""
    if isinstance(result, dict):
        upserted = result.get("upserted", 0)
        failed = result.get("failed", 0)
        total = result.get("total", 0)
        error = result.get("error")
        status = get_fixture_status(upserted, failed, error)

        return {
            "row": [
                table_name,
                str(upserted) if upserted > 0 else "[dim]0[/dim]",
                str(failed) if failed > 0 else "[dim]0[/dim]",
                str(total),
                status,
            ],
            "upserted": upserted,
            "failed": failed,
            "total": total,
        }

    status = f"[red]✗ {result}[/red]"
    return {
        "row": [table_name, "[dim]0[/dim]", "[dim]0[/dim]", "[dim]0[/dim]", status],
        "upserted": 0,
        "failed": 0,
        "total": 0,
    }


def get_fixture_status(upserted: int, failed: int, error: str | None) -> str:
    """Render the colored status cell for a fixture-result row."""
    max_error_length = 500

    if upserted > 0 and failed == 0:
        return f"[green]✓ {upserted} upserted[/green]"
    if upserted > 0 and failed > 0:
        return f"[yellow]⚠ {upserted} upserted, {failed} failed[/yellow]"
    if failed > 0:
        status = f"[red]✗ {failed} failed[/red]"
        if error:
            if len(error) > max_error_length:
                status += f"\n[dim]{error[: max_error_length - 3]}...[/dim]"
            else:
                status += f"\n[dim]{error}[/dim]"
        return status
    return "[dim]Empty fixture[/dim]"


def print_fixture_summary(total_upserted: int, total_failed: int, total_records: int) -> None:
    """Print fixture loading summary."""
    console = get_console()
    console.print("[bold]Summary:[/bold]")
    console.print(f"  • [green]Upserted: {total_upserted}[/green]")
    if total_failed > 0:
        console.print(f"  • [red]Failed: {total_failed}[/red]")
    console.print(f"  • [dim]Total records in fixtures: {total_records}[/dim]")
    console.print()


def display_available_tables() -> None:
    """Display available tables for export."""
    console = get_console()
    console.rule("[bold blue]Available Tables for Export", style="blue", align="left")
    console.print()

    fixtures_dir = get_settings().db.FIXTURE_PATH
    table = Table(show_header=True, header_style="bold blue", expand=True)
    table.add_column("Table Name", style="cyan", ratio=2)
    table.add_column("Export Order", justify="center", ratio=1)

    for idx, table_name in enumerate(COFFEE_SHOP_TABLES, 1):
        table.add_row(table_name, str(idx))

    console.print(table)
    console.print()
    console.print(f"[dim]Default output directory: {fixtures_dir}[/dim]")
    console.print(f"[dim]Total tables: {len(COFFEE_SHOP_TABLES)}[/dim]")
    console.print()


async def export_fixture_data(tables: str | None, output_dir: str | None, no_compress: bool) -> None:
    """Export fixture data from database."""
    console = get_console()
    console.rule("[bold blue]Exporting Database Fixtures", style="blue", align="left")
    console.print()

    table_list = None
    if tables:
        table_list = [t.strip() for t in tables.split(",")]
        console.print(f"[dim]Exporting specific tables: {', '.join(table_list)}[/dim]")
    else:
        console.print("[dim]Exporting all available tables[/dim]")

    output_path = Path(output_dir) if output_dir else None
    if output_path:
        console.print(f"[dim]Output directory: {output_path}[/dim]")

    compress = not no_compress
    console.print(f"[dim]Compression: {'enabled' if compress else 'disabled'}[/dim]")
    console.print()

    with console.status("[bold yellow]Exporting fixtures...", spinner="dots"):
        results = await export_fixtures(table_list, output_path, compress)

        if not results:
            console.print("[yellow]No tables found to export[/yellow]")
            return

        display_export_results(results)


def display_export_results(results: dict[str, Any]) -> None:
    """Display fixture export results."""
    console = get_console()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Table", style="cyan", width=30)
    table.add_column("Output File", style="dim", width=50)
    table.add_column("Status", width=50)

    total_success = 0
    total_failed = 0

    for table_name, result in results.items():
        if isinstance(result, str):
            if result.startswith("/") or result.endswith((".json", ".json.gz")):
                status = "[green]✓ Exported[/green]"
                file_display = result
                total_success += 1
            else:
                status = f"[red]✗ Failed: {result}[/red]"
                file_display = "[dim]N/A[/dim]"
                total_failed += 1
        else:
            status = f"[yellow]⚠ Unknown result: {result}[/yellow]"
            file_display = "[dim]N/A[/dim]"
            total_failed += 1

        table.add_row(table_name, file_display, status)

    console.print(table)
    console.print()
    print_export_summary(total_success, total_failed)


def print_export_summary(total_success: int, total_failed: int) -> None:
    """Print fixture export summary."""
    console = get_console()
    console.print("[bold]Summary:[/bold]")
    console.print(f"  • [green]Successfully exported: {total_success} tables[/green]")
    if total_failed > 0:
        console.print(f"  • [red]Failed: {total_failed} tables[/red]")
    console.print()

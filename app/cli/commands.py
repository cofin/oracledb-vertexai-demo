"""CLI commands for coffee shop demo application."""

from __future__ import annotations

from typing import Any

import rich_click as click
import structlog
from rich import get_console
from rich.prompt import Prompt

logger = structlog.get_logger()


# Coffee demo group for application-specific operations
@click.group(name="coffee", invoke_without_command=False, help="Coffee shop demo and AI operations.")
@click.pass_context
def coffee_demo_group(_: click.Context) -> None:
    """Coffee shop demo and AI operations."""


async def _fetch_products_to_embed(product_service: Any, force: bool) -> tuple[list[dict[str, Any]], str]:
    """Fetch products that need embeddings."""
    from rich import get_console

    console = get_console()
    with console.status("[bold yellow]Finding products to process...", spinner="dots"):
        if force:
            products = await product_service.driver.select(
                "SELECT id, name, description, embedding FROM product ORDER BY id",
            )
            message = f"[cyan]Processing ALL {len(products)} products (force mode)[/cyan]"
        else:
            products, total = await product_service.get_products_without_embeddings()
            message = f"[cyan]Processing {len(products)} products without embeddings from a total of {total}[/cyan]"

    return products, message


async def _process_product_batch(
    batch: list[dict[str, Any]],
    product_service: Any,
    vertex_ai_service: Any,
    start_idx: int,
    total_products: int,
) -> tuple[int, int]:
    """Process a batch of products for embedding generation.

    Returns:
        Tuple of (success_count, error_count)
    """
    from rich import get_console

    console = get_console()
    success_count = 0
    error_count = 0

    with console.status("[bold yellow]Generating embeddings...", spinner="dots") as status:
        for i, product in enumerate(batch):
            try:
                product_name = product.get("name", f"Product {product['id']}")
                global_idx = start_idx + i + 1
                status.update(f"[bold yellow]Processing {global_idx}/{total_products}: {product_name}...")

                # Generate embedding
                description = product.get("description", "")
                embedding = await vertex_ai_service.get_text_embedding(f"{product_name}: {description}")
                await product_service.update_embedding(product["id"], embedding)
                success_count += 1

            except Exception as e:  # noqa: BLE001
                error_count += 1
                logger.warning("Failed to process product", product_id=product.get("id"), error=str(e))

    return success_count, error_count


def _print_embedding_results(total_success: int, total_errors: int) -> None:
    """Print final embedding results."""
    from rich import get_console

    console = get_console()
    console.print("[bold]Final Results:[/bold]")
    console.print(f"[bold green]✓ Successfully processed: {total_success} products[/bold green]")
    if total_errors > 0:
        console.print(f"[bold red]✗ Failed to process: {total_errors} products[/bold red]")
    console.print()


@coffee_demo_group.command(
    name="bulk-embed",
    help="Run bulk embedding job for all products using Vertex AI.",
)
@click.option("--batch-size", default=50, help="Number of products to process in each batch (default: 50)")
@click.option("--force", "-f", is_flag=True, help="Re-embed all products, even if they already have embeddings")
def bulk_embed(batch_size: int, force: bool) -> None:
    """Run bulk embedding job for all products using Vertex AI."""
    from sqlspec.utils.sync_tools import run_

    console = get_console()
    console.rule("[bold blue]Bulk Product Embedding", style="blue", align="left")
    console.print()

    async def _bulk_embed_products() -> None:
        from app.config import db, db_manager
        from app.services import ProductService, VertexAIService
        from app.services._cache import CacheService

        # Use SQLSpec session directly
        async with db_manager.provide_session(db) as session:
            product_service = ProductService(session)
            cache_service = CacheService(session)
            vertex_ai_service = VertexAIService(cache_service=cache_service)

            # Get products to embed
            products, message = await _fetch_products_to_embed(product_service, force)
            console.print(message)

            if not products:
                if force:
                    console.print("[yellow]No products found in database[/yellow]")
                else:
                    console.print("[green]✓ All products already have embeddings![/green]")
                return

            console.print(f"[dim]Batch size: {batch_size}[/dim]")
            console.print()

            # Process products in batches
            total_success = 0
            total_errors = 0
            total_batches = (len(products) + batch_size - 1) // batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(products))
                batch = products[start_idx:end_idx]

                console.print(f"[bold]Processing batch {batch_num + 1}/{total_batches} ({len(batch)} products)[/bold]")

                success, errors = await _process_product_batch(
                    batch, product_service, vertex_ai_service, start_idx, len(products)
                )
                total_success += success
                total_errors += errors

                console.print(f"[green]✓ Batch {batch_num + 1} complete[/green]")
                console.print()

            # Show final results
            _print_embedding_results(total_success, total_errors)

    run_(_bulk_embed_products)()


@coffee_demo_group.command(name="clear-cache", help="Clear cache tables in the database.")
@click.option(
    "--include-exemplars",
    is_flag=True,
    help="Also clear intent exemplar embeddings (slow to regenerate)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clear_cache(include_exemplars: bool, force: bool) -> None:
    """Clear application caches.

    By default, clears response_cache and embedding_cache only.
    Intent exemplar embeddings are preserved (expensive to regenerate).
    """
    from sqlspec.utils.sync_tools import run_

    console = get_console()

    # Determine what will be cleared
    tables_to_clear = ["response_cache", "embedding_cache"]
    if include_exemplars:
        tables_to_clear.append("intent_exemplar")

    # Confirm operation unless forced
    if not force:
        console.print("[bold]Tables to clear:[/bold]")
        for table in tables_to_clear:
            console.print(f"  • {table}")

        if include_exemplars:
            console.print(
                "\n[bold red]⚠️  WARNING: Clearing intent exemplars will require regenerating embeddings![/bold red]"
            )

        confirm = Prompt.ask(
            "\n[bold red]Are you sure you want to clear these caches?[/bold red]",
            choices=["y", "n"],
            default="n",
        )
        if confirm.lower() != "y":
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

    async def _clear_cache() -> None:
        """Clear cache tables."""
        from app.config import db, db_manager
        from app.services._cache import CacheService

        async with db_manager.provide_session(db) as session:
            cache_service = CacheService(session)
            console.rule("[bold blue]Clearing Caches", style="blue", align="left")
            console.print()

            # Clear caches using the service
            deleted_count = await cache_service.invalidate_cache(cache_type=None, include_exemplars=include_exemplars)

            console.print(f"[green]✓ Cleared {deleted_count} cache records[/green]")
            console.print()

    run_(_clear_cache)()


@coffee_demo_group.command(name="model-info", help="Show information about currently configured AI models.")
def model_info() -> None:
    """Show information about currently configured AI models."""
    from app.lib.settings import get_settings
    from app.services import VertexAIService

    console = get_console()
    console.rule("[bold blue]AI Model Configuration", style="blue", align="left")
    console.print()

    # Show settings
    settings = get_settings()
    console.print(f"[bold]Chat Model:[/bold] {settings.app.GEMINI_MODEL}")
    console.print(f"[bold]Embedding Model:[/bold] {settings.app.EMBEDDING_MODEL}")
    console.print(f"[bold]Google Project:[/bold] {settings.app.GOOGLE_PROJECT_ID}")
    console.print("[bold]Embedding Dimensions:[/bold] 768")
    console.print()

    # Test model initialization
    console.print("[bold]🔍 Testing Model Initialization...[/bold]")
    try:
        VertexAIService()
        console.print("[bold green]✓ Successfully initialized![/bold green]")
    except Exception as e:  # noqa: BLE001
        console.print(f"[bold red]✗ Model initialization failed: {e}[/bold red]")
    console.print()


# Database fixture commands
@click.command(name="load-fixtures", help="Load application fixture data into the database.")
@click.option("--tables", "-t", help="Comma-separated list of specific tables to load (loads all if not specified)")
@click.option("--list", "list_fixtures", is_flag=True, help="List available fixture files")
def load_fixtures_cmd(tables: str | None, list_fixtures: bool) -> None:
    """Load application fixture data into the database."""

    if list_fixtures:
        _display_fixture_list()
        return

    _load_fixture_data(tables)


def _display_fixture_list() -> None:
    """Display available fixture files."""
    from pathlib import Path

    from rich.table import Table

    from app.lib.settings import get_settings

    console = get_console()
    console.rule("[bold blue]Available Fixture Files", style="blue", align="left")
    console.print()

    fixtures_dir = Path(get_settings().db.FIXTURE_PATH)
    if not fixtures_dir.exists():
        console.print(f"[yellow]Fixtures directory not found: {fixtures_dir}[/yellow]")
        return

    # Get all .json and .json.gz files
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
        # Extract table name from filename (remove .json or .json.gz)
        table_name = fixture_file.name.replace(".json.gz", "").replace(".json", "")
        try:
            import gzip
            import json

            # Load data to count records
            if fixture_file.suffix == ".gz":
                with gzip.open(fixture_file, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with fixture_file.open(encoding="utf-8") as f:
                    data = json.load(f)

            records = str(len(data)) if isinstance(data, list) else "1"
            size_bytes = fixture_file.stat().st_size
            size_mb = size_bytes / 1024 / 1024
            size = f"{size_mb:.1f} MB" if size_mb > 1 else f"{size_bytes / 1024:.1f} KB"
            status = "[green]Ready[/green]"
        except (OSError, PermissionError, json.JSONDecodeError) as e:
            records = "[dim]N/A[/dim]"
            size = "[dim]N/A[/dim]"
            status = f"[red]Error: {e}[/red]"

        table.add_row(table_name, fixture_file.name, records, size, status)

    console.print(table)
    console.print()


def _load_fixture_data(tables: str | None) -> None:
    """Load fixture data into database."""
    from sqlspec.utils.sync_tools import run_

    console = get_console()
    console.rule("[bold blue]Loading Database Fixtures", style="blue", align="left")
    console.print()

    # Parse tables if provided
    table_list = None
    if tables:
        table_list = [t.strip() for t in tables.split(",")]
        console.print(f"[dim]Loading specific tables: {', '.join(table_list)}[/dim]")
    else:
        console.print("[dim]Loading all available fixtures[/dim]")
    console.print()

    async def _load_fixtures() -> None:
        from app.db.utils import load_fixtures

        with console.status("[bold yellow]Loading fixtures...", spinner="dots"):
            results = await load_fixtures(table_list)

            if not results:
                console.print("[yellow]No fixture files found to load[/yellow]")
                return

            _display_fixture_results(results)

    run_(_load_fixtures)()


def _display_fixture_results(results: dict) -> None:
    """Display fixture loading results."""
    from rich.table import Table

    console = get_console()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Table", style="cyan", width=35)
    table.add_column("Status", width=100)

    total_upserted = 0
    total_failed = 0
    total_records = 0

    for table_name, result in results.items():
        row_data = _process_fixture_result(table_name, result)
        table.add_row(row_data["row"][0], row_data["row"][4])  # Only Table and Status columns

        total_upserted += row_data["upserted"]
        total_failed += row_data["failed"]
        total_records += row_data["total"]

    console.print(table)
    console.print()
    _print_fixture_summary(total_upserted, total_failed, total_records)


def _process_fixture_result(table_name: str, result: dict | int | str) -> dict:
    """Process individual fixture result for display."""
    if isinstance(result, dict):
        upserted = result.get("upserted", 0)
        failed = result.get("failed", 0)
        total = result.get("total", 0)
        error = result.get("error")

        status = _get_fixture_status(upserted, failed, error)

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
    if isinstance(result, int):
        # Legacy format
        status = "[green]✓ Success[/green]" if result > 0 else "[yellow]⚠ No new records[/yellow]"
        return {
            "row": [table_name, str(result), "[dim]0[/dim]", "[dim]-[/dim]", status],
            "upserted": result,
            "failed": 0,
            "total": 0,
        }
    # Error case
    status = f"[red]✗ {result}[/red]"
    return {
        "row": [table_name, "[dim]0[/dim]", "[dim]0[/dim]", "[dim]0[/dim]", status],
        "upserted": 0,
        "failed": 0,
        "total": 0,
    }


def _get_fixture_status(upserted: int, failed: int, error: str | None) -> str:
    """Get status text for fixture result."""
    max_error_length = 500

    if upserted > 0 and failed == 0:
        return f"[green]✓ {upserted} upserted[/green]"
    if upserted > 0 and failed > 0:
        return f"[yellow]⚠ {upserted} upserted, {failed} failed[/yellow]"
    if failed > 0:
        status = f"[red]✗ {failed} failed[/red]"
        if error:
            # Show detailed error information
            if len(error) > max_error_length:
                # Show first part of error with ellipsis
                status += f"\n[dim]{error[: max_error_length - 3]}...[/dim]"
            else:
                status += f"\n[dim]{error}[/dim]"
        return status
    return "[dim]Empty fixture[/dim]"


def _print_fixture_summary(total_upserted: int, total_failed: int, total_records: int) -> None:
    """Print fixture loading summary."""
    console = get_console()
    console.print("[bold]Summary:[/bold]")
    console.print(f"  • [green]Upserted: {total_upserted}[/green]")
    if total_failed > 0:
        console.print(f"  • [red]Failed: {total_failed}[/red]")
    console.print(f"  • [dim]Total records in fixtures: {total_records}[/dim]")
    console.print()

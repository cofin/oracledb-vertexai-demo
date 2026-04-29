"""CLI commands for coffee shop demo application."""

from __future__ import annotations

from typing import Any

import rich_click as click
import structlog
from rich import get_console
from rich.prompt import Prompt

logger = structlog.get_logger()




async def _fetch_products_to_embed(product_service: Any, force: bool) -> tuple[list[dict[str, Any]], str]:
    """Fetch products that need embeddings."""
    from rich import get_console

    console = get_console()
    with console.status("[bold yellow]Finding products to process...", spinner="dots"):
        products, _total = await product_service.get_products_for_embedding(force=force)

    label = "ALL products (force mode)" if force else "products without embeddings"
    return products, f"[cyan]Processing {len(products)} {label}[/cyan]"


async def _process_product_batch(
    batch: list[Any],
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
            product_id: int | None = None
            try:
                if isinstance(product, dict):
                    product_id = product["id"]
                    product_name = product.get("name", f"Product {product_id}")
                    description = product.get("description", "")
                else:
                    product_id = product.id
                    product_name = product.name or f"Product {product_id}"
                    description = product.description or ""

                global_idx = start_idx + i + 1
                status.update(f"[bold yellow]Processing {global_idx}/{total_products}: {product_name}...")

                # Generate embedding
                embedding = await vertex_ai_service.get_text_embedding(f"{product_name}: {description}")
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


async def _process_exemplar_batch(
    batch: list[Any],
    exemplar_service: Any,
    vertex_ai_service: Any,
    start_idx: int,
    total_exemplars: int,
) -> tuple[int, int]:
    """Re-embed a batch of intent_exemplar rows."""
    from rich import get_console

    console = get_console()
    success_count = 0
    error_count = 0

    with console.status("[bold yellow]Generating embeddings...", spinner="dots") as status:
        for i, row in enumerate(batch):
            exemplar_id: int | None = None
            try:
                exemplar_id = row["id"]
                phrase = row.get("phrase", "")

                global_idx = start_idx + i + 1
                status.update(f"[bold yellow]Processing {global_idx}/{total_exemplars}: {phrase[:60]}...")

                embedding = await vertex_ai_service.get_text_embedding(phrase, task_type="RETRIEVAL_DOCUMENT")
                updated = await exemplar_service.update_embedding(exemplar_id, embedding)
                if not updated:
                    error_count += 1
                    logger.warning("Failed to update exemplar", exemplar_id=exemplar_id, error="update affected 0 rows")
                    continue
                success_count += 1
            except Exception as e:  # noqa: BLE001
                error_count += 1
                logger.warning("Failed to embed exemplar", exemplar_id=exemplar_id, error=str(e))

    return success_count, error_count


async def _embed_in_batches(
    items: list[Any],
    batch_size: int,
    processor: Any,
) -> tuple[int, int]:
    """Iterate items in batches and aggregate (success, error) counts."""
    from rich import get_console

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


def _print_embedding_results(total_success: int, total_errors: int) -> None:
    """Print final embedding results."""
    from rich import get_console

    console = get_console()
    console.print("[bold]Results:[/bold]")
    console.print(f"[bold green]✓ Successfully processed: {total_success}[/bold green]")
    if total_errors > 0:
        console.print(f"[bold red]✗ Failed to process: {total_errors}[/bold red]")
    console.print()


@click.command(
    name="bulk-embed",
    help="Run bulk embedding job for products (and optionally intent exemplars) using Vertex AI.",
)
@click.option("--batch-size", default=50, help="Number of items to process in each batch (default: 50)")
@click.option("--force", "-f", is_flag=True, help="Re-embed all items, even if they already have embeddings")
@click.option(
    "--include-exemplars",
    is_flag=True,
    help="Also re-embed intent_exemplar phrases (required after dimension changes).",
)
def bulk_embed_cmd(batch_size: int, force: bool, include_exemplars: bool) -> None:
    """Run bulk embedding job for all products using Vertex AI."""
    from sqlspec.utils.sync_tools import run_

    console = get_console()
    console.rule("[bold blue]Bulk Embedding", style="blue", align="left")
    console.print()

    async def _bulk_embed() -> None:
        from google.genai import Client

        from app.config import db, db_manager
        from app.domain.products.services import ProductService, VertexAIService
        from app.domain.system.services import CacheService, ExemplarService
        from app.lib.settings import get_settings

        settings = get_settings()

        async with db_manager.provide_session(db) as session:
            product_service = ProductService(session)
            cache_service = CacheService(session)
            exemplar_service = ExemplarService(session)
            if settings.vertex_ai.PROJECT_ID:
                client = Client(
                    vertexai=True,
                    project=settings.vertex_ai.PROJECT_ID,
                    location=settings.vertex_ai.LOCATION,
                )
            else:
                client = Client(
                    api_key=settings.vertex_ai.API_KEY,
                )
            vertex_ai_service = VertexAIService(
                client=client,
                model=settings.vertex_ai.CHAT_MODEL,
                embedding_model=settings.vertex_ai.EMBEDDING_MODEL,
                embedding_dimensions=settings.vertex_ai.EMBEDDING_DIMENSIONS,
                cache_service=cache_service,
            )

            console.print("[bold]→ Products[/bold]")
            products, message = await _fetch_products_to_embed(product_service, force)
            console.print(message)

            product_success = product_errors = 0
            if products:
                console.print(f"[dim]Batch size: {batch_size}[/dim]\n")
                product_success, product_errors = await _embed_in_batches(
                    products,
                    batch_size,
                    lambda batch, start_idx, total: _process_product_batch(
                        batch, product_service, vertex_ai_service, start_idx, total
                    ),
                )
            else:
                console.print(
                    "[yellow]No products found in database[/yellow]"
                    if force
                    else "[green]✓ All products already have embeddings![/green]"
                )

            _print_embedding_results(product_success, product_errors)

            if include_exemplars:
                console.print()
                console.print("[bold]→ Intent exemplars[/bold]")
                exemplars, _total = await exemplar_service.get_exemplars_without_embeddings(force=force)
                label = "ALL exemplars (force mode)" if force else "exemplars without embeddings"
                console.print(f"[cyan]Processing {len(exemplars)} {label}[/cyan]")
                if not exemplars:
                    console.print(
                        "[yellow]No exemplars found in database[/yellow]"
                        if force
                        else "[green]✓ All exemplars already have embeddings![/green]"
                    )
                    return
                console.print(f"[dim]Batch size: {batch_size}[/dim]\n")
                exemplar_success, exemplar_errors = await _embed_in_batches(
                    exemplars,
                    batch_size,
                    lambda batch, start_idx, total: _process_exemplar_batch(
                        batch, exemplar_service, vertex_ai_service, start_idx, total
                    ),
                )
                _print_embedding_results(exemplar_success, exemplar_errors)

    run_(_bulk_embed)()


@click.command(name="clear-cache", help="Clear cache tables in the database.")
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
def clear_cache_cmd(include_exemplars: bool, force: bool) -> None:
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
        from app.domain.system.services import CacheService

        async with db_manager.provide_session(db) as session:
            cache_service = CacheService(session)
            console.rule("[bold blue]Clearing Caches", style="blue", align="left")
            console.print()

            # Clear caches using the service
            deleted_count = await cache_service.invalidate_cache(cache_type=None, include_exemplars=include_exemplars)

            console.print(f"[green]✓ Cleared {deleted_count} cache records[/green]")
            console.print()

    run_(_clear_cache)()


@click.command(name="model-info", help="Show information about currently configured AI models.")
def model_info_cmd() -> None:
    """Show information about currently configured AI models."""
    from sqlspec.utils.sync_tools import run_

    from app.config import db, db_manager
    from app.domain.products.services import VertexAIService
    from app.domain.system.services import CacheService
    from app.lib.settings import get_settings

    console = get_console()
    console.rule("[bold blue]AI Model Configuration", style="blue", align="left")
    console.print()

    # Show settings
    settings = get_settings()
    console.print(f"[bold]Chat Model:[/bold] {settings.vertex_ai.CHAT_MODEL}")
    console.print(f"[bold]Embedding Model:[/bold] {settings.vertex_ai.EMBEDDING_MODEL}")
    console.print(f"[bold]Google Project:[/bold] {settings.vertex_ai.PROJECT_ID}")
    console.print(f"[bold]Embedding Dimensions:[/bold] {settings.vertex_ai.EMBEDDING_DIMENSIONS}")
    console.print()

    # Test model initialization
    console.print("[bold]🔍 Testing Model Initialization...[/bold]")

    async def _check_vertex() -> None:
        from google.genai import Client
        async with db_manager.provide_session(db) as session:
            cache_service = CacheService(session)
            if settings.vertex_ai.PROJECT_ID:
                client = Client(
                    vertexai=True,
                    project=settings.vertex_ai.PROJECT_ID,
                    location=settings.vertex_ai.LOCATION,
                )
            else:
                client = Client(
                    api_key=settings.vertex_ai.API_KEY,
                )
            VertexAIService(
                client=client,
                model=settings.vertex_ai.CHAT_MODEL,
                embedding_model=settings.vertex_ai.EMBEDDING_MODEL,
                embedding_dimensions=settings.vertex_ai.EMBEDDING_DIMENSIONS,
                cache_service=cache_service,
            )
            console.print("[bold green]✓ Successfully initialized![/bold green]")

    try:
        run_(_check_vertex)()
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
    import gzip
    from pathlib import Path

    from rich.table import Table

    from app.lib.settings import get_settings
    from app.utils.serialization import from_json

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

            # Load data to count records
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


# Export fixtures command
@click.command(name="export-fixtures", help="Export database tables to fixture JSON files.")
@click.option("--tables", "-t", help="Comma-separated list of specific tables to export (exports all if not specified)")
@click.option("--output-dir", "-o", help="Custom output directory (defaults to configured fixtures directory)")
@click.option("--no-compress", is_flag=True, help="Export uncompressed JSON (default is gzipped)")
@click.option("--list", "list_tables", is_flag=True, help="List available tables for export")
def export_fixtures_cmd(tables: str | None, output_dir: str | None, no_compress: bool, list_tables: bool) -> None:
    """Export database tables to fixture JSON files."""

    if list_tables:
        _display_available_tables()
        return

    _export_fixture_data(tables, output_dir, no_compress)


def _display_available_tables() -> None:
    """Display available tables for export."""
    from rich.table import Table

    from app.db.utils import COFFEE_SHOP_TABLES
    from app.lib.settings import get_settings

    console = get_console()
    console.rule("[bold blue]Available Tables for Export", style="blue", align="left")
    console.print()

    settings = get_settings()
    fixtures_dir = settings.db.FIXTURE_PATH

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


def _export_fixture_data(tables: str | None, output_dir: str | None, no_compress: bool) -> None:
    """Export fixture data from database."""
    from pathlib import Path

    from sqlspec.utils.sync_tools import run_

    console = get_console()
    console.rule("[bold blue]Exporting Database Fixtures", style="blue", align="left")
    console.print()

    # Parse tables if provided
    table_list = None
    if tables:
        table_list = [t.strip() for t in tables.split(",")]
        console.print(f"[dim]Exporting specific tables: {', '.join(table_list)}[/dim]")
    else:
        console.print("[dim]Exporting all available tables[/dim]")

    # Parse output directory
    output_path = Path(output_dir) if output_dir else None
    if output_path:
        console.print(f"[dim]Output directory: {output_path}[/dim]")

    # Compression setting
    compress = not no_compress
    console.print(f"[dim]Compression: {'enabled' if compress else 'disabled'}[/dim]")
    console.print()

    async def _export_fixtures() -> None:
        from app.db.utils import export_fixtures

        with console.status("[bold yellow]Exporting fixtures...", spinner="dots"):
            results = await export_fixtures(table_list, output_path, compress)

            if not results:
                console.print("[yellow]No tables found to export[/yellow]")
                return

            _display_export_results(results)

    run_(_export_fixtures)()


def _display_export_results(results: dict) -> None:
    """Display fixture export results."""
    from rich.table import Table

    console = get_console()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Table", style="cyan", width=30)
    table.add_column("Output File", style="dim", width=50)
    table.add_column("Status", width=50)

    total_success = 0
    total_failed = 0

    for table_name, result in results.items():
        if isinstance(result, str):
            # Check if it's an error message or a file path
            if result.startswith("/") or result.endswith((".json", ".json.gz")):
                # It's a file path - success
                status = "[green]✓ Exported[/green]"
                file_display = result
                total_success += 1
            else:
                # It's an error message
                status = f"[red]✗ Failed: {result}[/red]"
                file_display = "[dim]N/A[/dim]"
                total_failed += 1
        else:
            # Unknown format
            status = f"[yellow]⚠ Unknown result: {result}[/yellow]"
            file_display = "[dim]N/A[/dim]"
            total_failed += 1

        table.add_row(table_name, file_display, status)

    console.print(table)
    console.print()
    _print_export_summary(total_success, total_failed)


def _print_export_summary(total_success: int, total_failed: int) -> None:
    """Print fixture export summary."""
    console = get_console()
    console.print("[bold]Summary:[/bold]")
    console.print(f"  • [green]Successfully exported: {total_success} tables[/green]")
    if total_failed > 0:
        console.print(f"  • [red]Failed: {total_failed} tables[/red]")
    console.print()

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
@click.pass_context  # pyright: ignore
def coffee_demo_group(_: dict[str, Any]) -> None:
    """Coffee shop demo and AI operations."""


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
        from app.server.deps import create_service_provider, provide_vertex_ai_service
        from app.services.product import ProductService

        # Create service providers
        product_provider = create_service_provider(ProductService)
        product_service_gen = product_provider()
        vertex_ai_service_gen = provide_vertex_ai_service()

        try:
            product_service = await anext(product_service_gen)
            vertex_ai_service = await anext(vertex_ai_service_gen)

            # Get products to embed
            with console.status("[bold yellow]Finding products to process...", spinner="dots"):
                if force:
                    products = await product_service.driver.select(
                        "SELECT id, name, description, embedding FROM product ORDER BY id",
                    )
                    console.print(f"[cyan]Processing ALL {len(products)} products (force mode)[/cyan]")
                else:
                    products, total = await product_service.get_products_without_embeddings()
                    console.print(
                        f"[cyan]Processing {len(products)} products without embeddings from a total of {total}[/cyan]"
                    )

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

                with console.status("[bold yellow]Generating embeddings...", spinner="dots") as status:
                    for i, product in enumerate(batch):
                        try:
                            product_name = product.get("name", f"Product {product['id']}")
                            global_idx = start_idx + i + 1
                            status.update(f"[bold yellow]Processing {global_idx}/{len(products)}: {product_name}...")

                            # Generate embedding
                            description = product.get("description", "")
                            embedding = await vertex_ai_service.create_embedding(f"{product_name}: {description}")
                            await product_service.update_embedding(product["id"], embedding)
                            total_success += 1

                        except Exception as e:  # noqa: BLE001
                            total_errors += 1
                            logger.warning("Failed to process product", product_id=product.get("id"), error=str(e))

                console.print(f"[green]✓ Batch {batch_num + 1} complete[/green]")
                console.print()

            # Show final results
            console.print("[bold]Final Results:[/bold]")
            console.print(f"[bold green]✓ Successfully processed: {total_success} products[/bold green]")
            if total_errors > 0:
                console.print(f"[bold red]✗ Failed to process: {total_errors} products[/bold red]")
            console.print()

        finally:
            await product_service_gen.aclose()
            await vertex_ai_service_gen.aclose()

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
        from app.server.deps import create_service_provider
        from app.services.cache import CacheService

        provider = create_service_provider(CacheService)
        service_gen = provider()

        try:
            cache_service = await anext(service_gen)

            console.rule("[bold blue]Clearing Caches", style="blue", align="left")
            console.print()

            # Clear caches using the service
            deleted_count = await cache_service.invalidate_cache(cache_type=None, include_exemplars=include_exemplars)

            console.print(f"[green]✓ Cleared {deleted_count} cache records[/green]")
            console.print()

        finally:
            await service_gen.aclose()

    run_(_clear_cache)()


@coffee_demo_group.command(name="model-info", help="Show information about currently configured AI models.")
def model_info() -> None:
    """Show information about currently configured AI models."""
    from app.lib.settings import get_settings
    from app.services.vertex_ai import VertexAIService

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

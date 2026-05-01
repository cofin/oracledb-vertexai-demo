# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Embedding lifecycle helpers for ``coffee`` CLI commands."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import rich_click as click
import structlog
from rich import get_console

if TYPE_CHECKING:
    from app.domain.products.services import ProductService, VertexAIService

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

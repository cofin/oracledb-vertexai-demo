# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Embedding lifecycle Rich console presenter for ``coffee`` CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

import rich_click as click
from rich import get_console

if TYPE_CHECKING:
    from app.domain.products.services import ProductService, VertexAIService

__all__ = ("generate_product_embeddings", "print_embedding_results", "validate_batch_size")


async def generate_product_embeddings(
    batch_size: int, force: bool, product_service: ProductService, vertex_ai_service: VertexAIService
) -> dict[str, int]:
    """Generate document-purpose embeddings for ``product`` and ``chat_route`` rows with Rich output.

    Returns:
        Summary dictionary with ``products_embedded``, ``routes_embedded``, and ``errors`` counts.
    """
    validate_batch_size(batch_size)

    console = get_console()
    console.rule("[bold blue]Product Embeddings", style="blue", align="left")
    console.print(f"[dim]Batch size: {batch_size} | Force: {force}[/dim]\n")

    def _report_batch(kind: str, batch_num: int, total_batches: int, successes: int, errors: int) -> None:
        label = "products" if kind == "products" else "chat routes"
        console.print(
            f"[green]✓ Completed {label} batch {batch_num}/{total_batches}[/green] "
            f"([cyan]{successes} embedded[/cyan], [yellow]{errors} errors[/yellow])"
        )

    summary = await vertex_ai_service.embed_missing_products(
        product_service, batch_size=batch_size, force=force, on_batch=_report_batch
    )
    total_embedded = summary["products_embedded"] + summary["routes_embedded"]
    if total_embedded == 0 and summary["errors"] == 0:
        console.print(
            "[yellow]No records found in database[/yellow]"
            if force
            else "[green]✓ All products and chat routes already have embeddings[/green]"
        )
    print_embedding_results(total_embedded, summary["errors"])
    return summary


def validate_batch_size(batch_size: int) -> None:
    """Validate embedding batch size before any service work starts."""
    if batch_size < 1:
        msg = "Batch size must be at least 1."
        raise click.ClickException(msg)


def print_embedding_results(total_success: int, total_errors: int) -> None:
    """Print final embedding results."""
    console = get_console()
    console.print("[bold]Results:[/bold]")
    console.print(f"[bold green]✓ Successfully processed: {total_success}[/bold green]")
    if total_errors > 0:
        console.print(f"[bold red]✗ Failed to process: {total_errors}[/bold red]")
    console.print()

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Background embedding tasks for the products domain."""

from __future__ import annotations

import structlog
from litestar_queues import RetryBackoff, task

from app.cli._helpers.embeddings import generate_product_embeddings
from app.domain.products.services import ProductService, VertexAIService
from app.lib.jobs import task_container_scope

__all__ = ("embed_missing_records",)

logger = structlog.get_logger()


@task(
    "products.embed_missing",
    queue="embeddings",
    retries=3,
    retry_backoff=RetryBackoff(initial_delay=2.0, multiplier=2.0, max_delay=30.0),
    unique_by="arguments",
    description="Generate 3072-dimension Vertex AI embeddings for product and chat_route rows.",
)
async def embed_missing_records(batch_size: int = 50, force: bool = False) -> dict[str, int]:
    """Embed product and ``chat_route`` records via the queue task pipeline.

    Args:
        batch_size: Maximum number of records processed per batch slice.
        force: Whether to re-embed rows that already have vectors.

    Returns:
        Summary counts of embedded products, embedded routes, and errors.
    """
    async with task_container_scope() as container:
        product_service = await container.get(ProductService)
        vertex_ai_service = await container.get(VertexAIService)
        summary = await generate_product_embeddings(
            batch_size=batch_size, force=force, product_service=product_service, vertex_ai_service=vertex_ai_service
        )

    logger.info(
        "Completed background embedding job",
        products_embedded=summary["products_embedded"],
        routes_embedded=summary["routes_embedded"],
        errors=summary["errors"],
        force=force,
    )
    return summary

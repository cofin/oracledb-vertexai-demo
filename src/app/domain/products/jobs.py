# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Background embedding tasks for the products domain."""

from __future__ import annotations

import structlog
from litestar_queues import RetryBackoff, task

from app.cli._helpers.embeddings import (
    chat_route_embedding_input,
    product_embedding_input,
    update_chat_route_embedding,
    update_product_embedding,
)
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
    """Embed product and ``chat_route`` records in the background.

    Args:
        batch_size: Maximum number of records processed per batch slice.
        force: Whether to re-embed rows that already have vectors.

    Returns:
        Summary counts of embedded products, embedded routes, and errors.
    """
    del batch_size
    products_embedded = 0
    routes_embedded = 0
    total_errors = 0

    async with task_container_scope() as container:
        product_service = await container.get(ProductService)
        vertex_ai_service = await container.get(VertexAIService)

        products, _product_total = await product_service.get_products_for_embedding(force=force)
        for product in products:
            product_id, product_name, description = product_embedding_input(product)
            try:
                products_embedded, total_errors = await update_product_embedding(
                    product_service=product_service,
                    vertex_ai_service=vertex_ai_service,
                    product_id=product_id,
                    product_name=product_name,
                    description=description,
                    success_count=products_embedded,
                    error_count=total_errors,
                )
            except Exception as exc:
                total_errors += 1
                logger.warning("Background product embedding failed", product_id=product_id, error=str(exc))

        routes, _route_total = await product_service.get_chat_routes_for_embedding(force=force)
        for route in routes:
            route_id, _route_title, route_text = chat_route_embedding_input(route)
            try:
                routes_embedded, total_errors = await update_chat_route_embedding(
                    product_service=product_service,
                    vertex_ai_service=vertex_ai_service,
                    route_id=route_id,
                    route_text=route_text,
                    success_count=routes_embedded,
                    error_count=total_errors,
                )
            except Exception as exc:
                total_errors += 1
                logger.warning("Background chat_route embedding failed", route_id=route_id, error=str(exc))

    logger.info(
        "Completed background embedding job",
        products_embedded=products_embedded,
        routes_embedded=routes_embedded,
        errors=total_errors,
        force=force,
    )
    return {
        "products_embedded": products_embedded,
        "routes_embedded": routes_embedded,
        "errors": total_errors,
    }

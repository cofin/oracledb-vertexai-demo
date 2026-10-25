# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Vertex AI embedding and structured content generation service."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import structlog
from google.genai.types import EmbedContentConfig, GenerateContentConfig

if TYPE_CHECKING:
    from google.genai import Client

    from app.domain.products.services._products import ProductService

__all__ = ("EMBEDDING_PURPOSE_INSTRUCTIONS", "GEMINI_EMBEDDING_2_MODEL", "BatchProgressCallback", "VertexAIService")

BatchProgressCallback = Callable[[str, int, int, int, int], None]

GEMINI_EMBEDDING_2_MODEL = "gemini-embedding-2"
EMBEDDING_PURPOSE_INSTRUCTIONS = {
    "query": (
        "Task: Generate an embedding for a search query to retrieve relevant "
        "Cymbal Coffee menu and store availability documents."
    ),
    "document": (
        "Task: Generate an embedding for a document that can be retrieved by Cymbal Coffee customer search queries."
    ),
}

logger = structlog.get_logger()


class VertexAIService:
    """Service for interacting with Google Vertex AI embeddings and structured generation."""

    __slots__ = ("cache_service", "client", "embedding_dimensions", "embedding_model", "model")

    def __init__(
        self, client: Client, model: str, embedding_model: str, embedding_dimensions: int, cache_service: Any
    ) -> None:
        self.client = client
        self.model = model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.cache_service = cache_service

    async def get_text_embedding(
        self, text: str, *, embedding_purpose: str = "document", return_cache_status: bool = False
    ) -> Any:
        """Compute or retrieve a cached text embedding vector."""
        cached = await self.cache_service.get_embedding(text, self.embedding_model)
        if cached:
            return (cached, True) if return_cache_status else cached

        content = _embedding_content(self.embedding_model, text, embedding_purpose)
        response = await self.client.aio.models.embed_content(
            model=self.embedding_model,
            contents=content,
            config=EmbedContentConfig(output_dimensionality=self.embedding_dimensions),
        )
        embedding_list = response.embeddings
        if not embedding_list or not embedding_list[0].values:
            return (None, False) if return_cache_status else None
        embedding = embedding_list[0].values
        await self.cache_service.save_embedding(text, embedding, self.embedding_model)
        return (embedding, False) if return_cache_status else embedding

    async def generate_structured_content(self, *, model: str, contents: str, config: GenerateContentConfig) -> Any:
        """Generate structured content through the shared Vertex AI client."""
        return await self.client.aio.models.generate_content(model=model, contents=contents, config=config)

    async def embed_missing_products(
        self,
        product_service: ProductService,
        *,
        batch_size: int = 50,
        force: bool = False,
        on_batch: BatchProgressCallback | None = None,
    ) -> dict[str, int]:
        """Embed missing or forced ``product`` and ``chat_route`` rows in pure async slices.

        Args:
            product_service: Product catalog service providing row queries and updates.
            batch_size: Maximum number of records processed per batch slice.
            force: Whether to recompute vectors for rows that already have embeddings.
            on_batch: Optional callback invoked after each slice with
                ``(kind, batch_number, total_batches, batch_successes, batch_errors)``.

        Returns:
            Dictionary containing ``products_embedded``, ``routes_embedded``, and ``errors``.
        """
        effective_batch = max(1, batch_size)
        products, _ = await product_service.get_products_for_embedding(force=force)
        prod_success, prod_errors = await self._embed_product_slices(
            products, product_service=product_service, batch_size=effective_batch, on_batch=on_batch
        )

        routes, _ = await product_service.get_chat_routes_for_embedding(force=force)
        route_success, route_errors = await self._embed_route_slices(
            routes, product_service=product_service, batch_size=effective_batch, on_batch=on_batch
        )

        return {
            "products_embedded": prod_success,
            "routes_embedded": route_success,
            "errors": prod_errors + route_errors,
        }

    async def _embed_product_slices(
        self,
        products: list[dict[str, Any]],
        *,
        product_service: ProductService,
        batch_size: int,
        on_batch: BatchProgressCallback | None,
    ) -> tuple[int, int]:
        if not products:
            return 0, 0
        total_success = 0
        total_errors = 0
        total_batches = (len(products) + batch_size - 1) // batch_size
        for batch_index in range(total_batches):
            slice_rows = products[batch_index * batch_size : (batch_index + 1) * batch_size]
            batch_ok = 0
            batch_err = 0
            for product in slice_rows:
                if await self._embed_single_product(product, product_service=product_service):
                    batch_ok += 1
                else:
                    batch_err += 1
            total_success += batch_ok
            total_errors += batch_err
            if on_batch is not None:
                on_batch("products", batch_index + 1, total_batches, batch_ok, batch_err)
        return total_success, total_errors

    async def _embed_single_product(self, product: dict[str, Any], *, product_service: ProductService) -> bool:
        product_id: int | None = None
        try:
            product_id, product_name, description = _product_embedding_input(product)
            embedding = await self.get_text_embedding(f"{product_name}: {description}", embedding_purpose="document")
            updated = bool(embedding) and await product_service.update_embedding(product_id, embedding)
        except Exception as exc:
            logger.warning("Failed to process product embedding", product_id=product_id, error=str(exc))
            return False
        if not updated:
            logger.warning("Failed to update product embedding", product_id=product_id)
        return updated

    async def _embed_route_slices(
        self,
        routes: list[dict[str, Any]],
        *,
        product_service: ProductService,
        batch_size: int,
        on_batch: BatchProgressCallback | None,
    ) -> tuple[int, int]:
        if not routes:
            return 0, 0
        total_success = 0
        total_errors = 0
        total_batches = (len(routes) + batch_size - 1) // batch_size
        for batch_index in range(total_batches):
            slice_rows = routes[batch_index * batch_size : (batch_index + 1) * batch_size]
            batch_ok = 0
            batch_err = 0
            for route in slice_rows:
                if await self._embed_single_route(route, product_service=product_service):
                    batch_ok += 1
                else:
                    batch_err += 1
            total_success += batch_ok
            total_errors += batch_err
            if on_batch is not None:
                on_batch("chat_routes", batch_index + 1, total_batches, batch_ok, batch_err)
        return total_success, total_errors

    async def _embed_single_route(self, route: dict[str, Any], *, product_service: ProductService) -> bool:
        route_id: int | None = None
        try:
            route_id, route_text = _chat_route_embedding_input(route)
            embedding = await self.get_text_embedding(route_text, embedding_purpose="document")
            updated = bool(embedding) and await product_service.update_chat_route_embedding(route_id, embedding)
        except Exception as exc:
            logger.warning("Failed to process chat_route embedding", route_id=route_id, error=str(exc))
            return False
        if not updated:
            logger.warning("Failed to update chat_route embedding", route_id=route_id)
        return updated


def _product_embedding_input(product: dict[str, Any]) -> tuple[int, str, str]:
    product_id = int(product["id"])
    return product_id, str(product.get("name", f"Product {product_id}")), str(product.get("description", ""))


def _chat_route_embedding_input(route: dict[str, Any]) -> tuple[int, str]:
    route_id = int(route["id"])
    route_label = str(route.get("route_label", ""))
    title = str(route.get("title", f"Route {route_id}"))
    exemplar_text = str(route.get("exemplar_text", ""))
    keywords = str(route.get("keywords", ""))
    return route_id, f"{route_label} | {title}: {exemplar_text} ({keywords})"


def _embedding_content(model: str, text: str, embedding_purpose: str) -> str:
    if GEMINI_EMBEDDING_2_MODEL not in model:
        return text
    instruction = EMBEDDING_PURPOSE_INSTRUCTIONS.get(embedding_purpose)
    if instruction is None:
        return text
    return f"{instruction}\n\n{text}"

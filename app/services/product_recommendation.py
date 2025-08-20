"""Product recommendation service."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.services.intent import IntentService
    from app.services.product import ProductService

logger = structlog.get_logger()


class ProductRecommendationService:
    """Product recommendation service."""

    def __init__(self, intent_service: IntentService, products_service: ProductService) -> None:
        self.intent_service = intent_service
        self.products_service = products_service

    async def recommend_products(
        self,
        query: str,
        query_embedding: list[float],
        chat_metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Sequence[int], dict, float | None]:
        """Route question through semantic intent detection and product matching."""

        chat_metadata = chat_metadata or {}
        vector_timings: dict[str, float] = {"embedding_ms": 0.0, "oracle_ms": 0.0, "total_ms": 0.0}
        similarity_score = None

        intent, confidence, exemplar, _ = await self.intent_service.route_intent_single(query, query_embedding)

        logger.info(
            "Intent routing decision",
            query=query,
            intent=intent,
            confidence=confidence,
            exemplar=exemplar,
        )

        chat_metadata["intent_routing"] = {
            "detected_intent": intent,
            "confidence": confidence,
            "matched_exemplar": exemplar,
        }

        if intent == "PRODUCT_RAG":
            matched_documents, product_vector_timings = await self.products_service.search_by_vector_with_timing(
                query_embedding, limit=4
            )
            vector_timings.update(product_vector_timings)
            matched_product_ids = [match["id"] for match in matched_documents]

            chat_metadata["embedding_cache_hit"] = False

            if matched_product_ids:
                similar_products = []
                for product_id in matched_product_ids[:2]:
                    product = await self.products_service.get_by_id(product_id)
                    if product:
                        similar_products.append(product)

                chat_metadata["product_matches"] = [
                    f"- {product.name}: {product.description}" for product in similar_products
                ]
                similarity_score = 1 - matched_documents[0]["distance"] if matched_documents else None

                return chat_metadata, matched_product_ids, vector_timings, similarity_score

        return chat_metadata, [], vector_timings, similarity_score

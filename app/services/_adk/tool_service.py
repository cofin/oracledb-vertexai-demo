"""Agent Tools Service containing business logic for ADK tool operations.

This service consolidates all the business logic for agent tools, ensuring
clean separation between ADK integration and core functionality.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

import structlog

from app.services.base import SQLSpecService

if TYPE_CHECKING:
    from app.services._intent import IntentService
    from app.services._metrics import MetricsService
    from app.services._product import ProductService
    from app.services._store import StoreService
    from app.services._vertex_ai import VertexAIService

logger = structlog.get_logger()


class AgentToolsService(SQLSpecService):
    """Service containing all agent tool business logic."""

    def __init__(
        self,
        driver: Any,
        product_service: ProductService,
        metrics_service: MetricsService,
        intent_service: IntentService,
        vertex_ai_service: VertexAIService,
        store_service: StoreService,
    ) -> None:
        """Initialize agent tools service."""
        super().__init__(driver)
        self.product_service = product_service
        self.metrics_service = metrics_service
        self.intent_service = intent_service
        self.vertex_ai_service = vertex_ai_service
        self.store_service = store_service

    async def search_products_by_vector(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Search for coffee products using vector similarity."""
        start_time = time.time()

        embedding_start = time.time()
        query_embedding, embedding_cache_hit = await self.vertex_ai_service.get_text_embedding(
            query, return_cache_status=True
        )
        embedding_ms = (time.time() - embedding_start) * 1000

        search_start = time.time()
        products = await self.product_service.search_by_vector(
            query_embedding=query_embedding,
            similarity_threshold=similarity_threshold,
            limit=limit,
        )
        search_ms = (time.time() - search_start) * 1000

        total_ms = (time.time() - start_time) * 1000

        product_list: list[dict[str, Any]] = [
            {
                "id": str(product.get("id")),
                "name": product.get("name"),
                "description": product.get("description"),
                "price": float(product.get("current_price", 0.0)),
                "similarity_score": float(product.get("similarity_score", 0.0)),
                "metadata": {},
            }
            for product in products
        ]

        sql_query = """SELECT p.id, p.name, p.description, p.current_price,
       1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) as similarity
FROM product p
WHERE 1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) > :threshold
ORDER BY similarity DESC
FETCH FIRST :limit ROWS ONLY"""

        return {
            "products": product_list,
            "timing": {"total_ms": total_ms, "embedding_ms": embedding_ms, "search_ms": search_ms},
            "embedding_cache_hit": embedding_cache_hit,
            "vector_search_cache_hit": False,  # This is no longer tracked in ProductService
            "sql_query": sql_query,
            "params": {"similarity_threshold": similarity_threshold, "limit": limit},
            "results_count": len(product_list),
        }

    async def get_product_details(self, product_id: str) -> dict[str, Any]:
        """Get detailed information about a specific product by ID or name."""
        product = None
        try:
            # Try to convert to int for ID lookup
            product_id_int = int(product_id)
            product = await self.product_service.get_by_id(product_id_int)
        except (ValueError, TypeError):
            # If not an int, assume it's a name
            product = await self.product_service.get_by_name(product_id)

        if not product:
            return {"error": "Product not found"}

        return {
            "id": str(product.id),
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "category": product.category,
            "in_stock": product.in_stock,
            "metadata": product.metadata or {},
        }

    async def classify_intent(self, query: str) -> dict[str, Any]:
        """Classify user intent using vector-based classification."""
        start_time = time.time()

        try:
            result = await self.intent_service.classify_intent(query)
            total_ms = (time.time() - start_time) * 1000

            sql_query = """WITH query_embedding AS (
        SELECT intent, phrase,
            1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) AS similarity,
            confidence_threshold,
            usage_count
        FROM intent_exemplar)
SELECT intent, phrase, similarity, confidence_threshold, usage_count
FROM query_embedding
WHERE similarity > :min_threshold
ORDER BY similarity DESC
FETCH FIRST :limit ROWS ONLY"""

            return {
                "intent": result.intent,
                "confidence": float(result.confidence),
                "exemplar_phrase": result.exemplar_phrase,
                "embedding_cache_hit": result.embedding_cache_hit,
                "fallback_used": result.fallback_used,
                "timing_ms": total_ms,
                "sql_query": sql_query,
            }
        except (ValueError, TypeError, AttributeError) as e:
            total_ms = (time.time() - start_time) * 1000
            return {
                "intent": "GENERAL_CONVERSATION",
                "confidence": 0.5,
                "exemplar_phrase": "",
                "embedding_cache_hit": False,
                "fallback_used": True,
                "error": str(e),
                "timing_ms": total_ms,
                "sql_query": "-- Error occurred during intent classification",
            }

    async def record_search_metric(
        self,
        session_id: str,
        query_text: str,
        intent: str,
        vector_results: list[dict[str, Any]],
        total_response_time_ms: int,
        vector_search_time_ms: int = 0,
        embedding_time_ms: int = 0,
        query_id: str | None = None,
    ) -> dict[str, Any]:
        """Record metrics for a search operation."""
        try:
            from app.schemas import SearchMetricsCreate
            avg_similarity = 0.0
            if vector_results:
                similarity_scores = [
                    result["similarity_score"]
                    for result in vector_results
                    if isinstance(result, dict) and "similarity_score" in result
                ]

                if similarity_scores:
                    avg_similarity = sum(similarity_scores) / len(similarity_scores)

            metrics_data = SearchMetricsCreate(
                query_id=query_id or str(uuid.uuid4()),
                user_id=session_id,
                search_time_ms=float(total_response_time_ms),
                embedding_time_ms=float(embedding_time_ms),
                oracle_time_ms=float(vector_search_time_ms),
                similarity_score=avg_similarity,
                result_count=len(vector_results),
            )
            await self.metrics_service.record_search(metrics_data)
        except (ValueError, TypeError, AttributeError) as e:
            return {"status": "failed", "error": str(e)}
        else:
            return {"status": "recorded", "session_id": session_id}

    async def get_all_store_locations(self) -> list[dict[str, Any]]:
        """Get all store locations and information."""
        try:
            stores = await self.store_service.get_all_stores()
            return [
                {
                    "id": store.id,
                    "name": store.name,
                    "address": store.address,
                    "city": store.city,
                    "state": store.state,
                    "zip": store.zip,
                    "phone": store.phone,
                    "hours": store.hours or {},
                    "metadata": store.metadata or {},
                }
                for store in stores
            ]
        except Exception:
            logger.exception("Failed to retrieve store locations")
            return []

    async def find_stores_by_location(self, city: str | None = None, state: str | None = None) -> list[dict[str, Any]]:
        """Find stores in a specific location."""
        try:
            if city:
                stores = await self.store_service.find_stores_by_city(city)
            elif state:
                stores = await self.store_service.find_stores_by_state(state)
            else:
                stores = await self.store_service.get_all_stores()

            return [
                {
                    "id": store.id,
                    "name": store.name,
                    "address": store.address,
                    "city": store.city,
                    "state": store.state,
                    "phone": store.phone,
                    "hours": store.hours or {},
                }
                for store in stores
            ]
        except Exception:
            logger.exception("Failed to find stores by location", city=city, state=state)
            return []

    async def get_store_hours(self, store_id: int) -> dict[str, Any]:
        """Get store hours for a specific store."""
        try:
            store = await self.store_service.get_store_by_id(store_id)
            if not store:
                return {"error": "Store not found"}
        except Exception:
            logger.exception("Failed to get store hours", store_id=store_id)
            return {"error": "Failed to retrieve store hours"}
        else:
            return {
                "store_name": store.name,
                "hours": store.hours or {},
                "phone": store.phone,
                "address": store.address,
            }

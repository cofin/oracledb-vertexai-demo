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
    from app.services.intent import IntentService
    from app.services.metrics import MetricsService
    from app.services.product import ProductService
    from app.services.store import StoreService
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class AgentToolsService(SQLSpecService):
    """Service containing all agent tool business logic.

    This service acts as a facade over the other services, providing
    high-level operations for agent tools while maintaining clean
    session management.
    """

    def __init__(
        self,
        driver: Any,
        product_service: ProductService,
        metrics_service: MetricsService,
        intent_service: IntentService,
        vertex_ai_service: VertexAIService,
        store_service: StoreService,
    ) -> None:
        """Initialize agent tools service.

        Args:
            driver: Database driver
            product_service: Service for product operations
            metrics_service: Service for metrics operations
            intent_service: Service for intent classification
            vertex_ai_service: Service for AI operations
            store_service: Service for store operations
        """
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
        """Search for coffee products using vector similarity.

        Args:
            query: Customer's product query or description
            limit: Maximum number of products to return (1-20, default 5)
            similarity_threshold: Minimum similarity score 0.0-1.0 (default 0.7)

        Returns:
            Dict containing products, timing info, and SQL query used
        """
        start_time = time.time()

        # Time embedding generation and track cache hit
        embedding_start = time.time()
        query_embedding, embedding_cache_hit = await self.vertex_ai_service.get_text_embedding_with_cache_status(query)
        embedding_ms = (time.time() - embedding_start) * 1000

        # Time vector search with result caching
        search_start = time.time()
        products, vector_search_cache_hit = await self.product_service.vector_similarity_search_with_cache(
            query_embedding=query_embedding,
            similarity_threshold=similarity_threshold,
            limit=limit,
        )
        search_ms = (time.time() - search_start) * 1000

        total_ms = (time.time() - start_time) * 1000

        product_list = [
            {
                "id": str(product.id),
                "name": product.name,
                "description": product.description,
                "price": float(product.price),
                "similarity_score": float(product.similarity_score),
                "metadata": product.metadata or {},
            }
            for product in products
        ]

        # Include actual SQL query template for UI display
        sql_query = """SELECT p.id, p.name, p.description, p.price,
       1 - (p.embedding <=> %s) as similarity
FROM product p
WHERE 1 - (p.embedding <=> %s) > %s
ORDER BY similarity DESC
LIMIT %s"""

        return {
            "products": product_list,
            "timing": {"total_ms": total_ms, "embedding_ms": embedding_ms, "search_ms": search_ms},
            "embedding_cache_hit": embedding_cache_hit,
            "vector_search_cache_hit": vector_search_cache_hit,
            "sql_query": sql_query,
            "params": {"similarity_threshold": similarity_threshold, "limit": limit},
            "results_count": len(product_list),
        }

    async def get_product_details(self, product_id: str) -> dict[str, Any]:
        """Get detailed information about a specific product by ID or name.

        Args:
            product_id: Product UUID or name to look up

        Returns:
            Product details or error message
        """
        try:
            # Try UUID lookup first (UUID string is 36 characters with hyphens)
            uuid_length = 36
            if len(product_id) == uuid_length and "-" in product_id:
                product = await self.product_service.get_by_id(uuid.UUID(product_id))
            else:
                # Try name lookup
                products = await self.product_service.search_by_name(product_id, limit=1)
                product = products[0] if products else None

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
        except (ValueError, TypeError, AttributeError) as e:
            return {"error": f"Failed to lookup product: {e!s}"}

    async def classify_intent(self, query: str) -> dict[str, Any]:
        """Classify user intent using vector-based classification.

        Args:
            query: User's message to classify

        Returns:
            Intent classification results with timing info
        """
        start_time = time.time()

        try:
            result = await self.intent_service.classify_intent(query)
            total_ms = (time.time() - start_time) * 1000

            # Include actual PostgreSQL query for intent classification
            sql_query = """WITH query_embedding AS (
        SELECT intent, phrase,
            1 - (embedding <=> $1) AS similarity,
            confidence_threshold,
            usage_count
        FROM intent_exemplar)
SELECT intent, phrase, similarity, confidence_threshold, usage_count
FROM query_embedding
WHERE similarity > $2
ORDER BY similarity DESC
LIMIT $3"""

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
    ) -> dict[str, Any]:
        """Record metrics for a search operation.

        Args:
            session_id: Session identifier
            query_text: The search query
            intent: Detected intent
            vector_results: Vector search results
            total_response_time_ms: Total response time
            vector_search_time_ms: Time spent on vector search

        Returns:
            Status of metric recording
        """
        try:
            # Calculate average similarity score from vector results
            avg_similarity = 0.0
            if vector_results:
                similarity_scores = [
                    result["similarity_score"]
                    for result in vector_results
                    if isinstance(result, dict) and "similarity_score" in result
                ]

                if similarity_scores:
                    avg_similarity = sum(similarity_scores) / len(similarity_scores)

            await self.metrics_service.record_search_metric(
                session_id=session_id,  # Keep as string
                query_text=query_text,
                intent=intent,
                vector_search_results=len(vector_results),  # Fix: pass count not list
                total_response_time_ms=int(total_response_time_ms),
                vector_search_time_ms=vector_search_time_ms,
                avg_similarity_score=avg_similarity,
            )
        except (ValueError, TypeError, AttributeError) as e:
            return {"status": "failed", "error": str(e)}
        else:
            return {"status": "recorded", "session_id": session_id}

    async def get_all_store_locations(self) -> list[dict[str, Any]]:
        """Get all store locations and information.

        Returns:
            List of all coffee shop locations with details
        """
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
        """Find stores in a specific location.

        Args:
            city: City name to search for (optional)
            state: State to search for (optional)

        Returns:
            List of stores matching the location criteria
        """
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
        """Get store hours for a specific store.

        Args:
            store_id: Store ID

        Returns:
            Store hours information
        """
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

"""Vector search demo service."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

import structlog

from app import schemas

if TYPE_CHECKING:
    from app.services.embedding_cache import EmbeddingCache
    from app.services.product import ProductService
    from app.services.search_metrics import SearchMetricsService
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class VectorDemoService:
    """Vector search demo service."""

    def __init__(
        self,
        vertex_ai_service: VertexAIService,
        products_service: ProductService,
        metrics_service: SearchMetricsService,
        embedding_cache: EmbeddingCache,
    ) -> None:
        self.vertex_ai_service = vertex_ai_service
        self.products_service = products_service
        self.metrics_service = metrics_service
        self.embedding_cache = embedding_cache

    async def search(self, query: str) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
        """Interactive vector search demonstration."""
        full_request_start = time.time()
        detailed_timings: dict[str, float] = {}

        embedding_start = time.time()
        embedding, from_cache = await self.embedding_cache.get_embedding(query, self.vertex_ai_service)
        embedding_time = (time.time() - embedding_start) * 1000
        detailed_timings["embedding_ms"] = embedding_time

        search_start = time.time()
        results, vector_timings = await self.products_service.search_by_vector_with_timing(embedding, limit=5)
        vector_timings["embedding_ms"] = embedding_time
        detailed_timings["similarity_search_total_ms"] = (time.time() - search_start) * 1000
        detailed_timings.update(vector_timings)

        embedding_cache_hit = from_cache

        metrics_record_start = time.time()
        await self.metrics_service.record_search(
            schemas.SearchMetricsCreate(
                query_id=schemas.QueryId(str(uuid.uuid4())),
                user_id=schemas.UserId("demo_user"),
                search_time_ms=(time.time() - full_request_start) * 1000,
                embedding_time_ms=detailed_timings["embedding_ms"],
                oracle_time_ms=detailed_timings["oracle_ms"],
                ai_time_ms=0,
                intent_time_ms=0,
                similarity_score=1 - results[0]["distance"] if results else 0,
                result_count=len(results),
            )
        )
        detailed_timings["metrics_recording_ms"] = (time.time() - metrics_record_start) * 1000

        format_results_start = time.time()
        demo_results = [
            {
                "name": r["name"],
                "description": r["description"],
                "similarity": f"{(1 - r['distance']) * 100:.1f}%",
                "distance": r["distance"],
            }
            for r in results
        ]
        detailed_timings["results_formatting_ms"] = (time.time() - format_results_start) * 1000

        pre_template_total = (time.time() - full_request_start) * 1000

        known_duration = sum([
            detailed_timings.get("similarity_search_total_ms", 0),
            detailed_timings.get("metrics_recording_ms", 0),
            detailed_timings.get("results_formatting_ms", 0),
        ])
        detailed_timings["pre_template_overhead_ms"] = pre_template_total - known_duration

        logger.info(
            "vector_demo_detailed_timings",
            query=query[:50],
            timings=detailed_timings,
            cache_hit=embedding_cache_hit,
        )

        return demo_results, detailed_timings, embedding_cache_hit

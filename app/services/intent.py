"""Intent detection using Oracle 23AI native vector similarity search."""

from __future__ import annotations

import array
from typing import TYPE_CHECKING

import structlog

from app.config import INTENT_THRESHOLDS, VECTOR_SEARCH_CONFIG

if TYPE_CHECKING:
    from app.db.repositories.intent_exemplar import IntentExemplarRepository
    from app.services.embedding_cache import EmbeddingCache
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class IntentService:
    """Oracle 23AI native vector similarity search for intent routing."""

    def __init__(
        self,
        exemplar_repository: IntentExemplarRepository,
        vertex_ai_service: VertexAIService,
        embedding_cache: EmbeddingCache | None = None,
    ) -> None:
        """Initialize with repository, Vertex AI service and optional embedding cache."""
        self.exemplar_repository = exemplar_repository
        self.vertex_ai = vertex_ai_service
        self.cache = embedding_cache

    async def route_intent(self, query: str, query_embedding: list[float] | None = None) -> tuple[list[tuple[str, float, str]], bool]:
        """Route intent using Oracle's native vector similarity search."""
        embedding_cache_hit = False
        if query_embedding is None:
            if self.cache:
                query_embedding, embedding_cache_hit = await self.cache.get_embedding(query, self.vertex_ai)
            else:
                query_embedding = await self.vertex_ai.create_embedding(query)
        else:
            embedding_cache_hit = True

        async with self.exemplar_repository.connection.cursor() as cursor:
            embedding_array = array.array("f", query_embedding)
            await cursor.execute(
                """
                SELECT
                    intent,
                    phrase,
                    1 - VECTOR_DISTANCE(embedding, :query_embedding, COSINE) AS similarity_score
                FROM intent_exemplar
                WHERE 1 - VECTOR_DISTANCE(embedding, :query_embedding, COSINE) > :min_threshold
                ORDER BY similarity_score DESC
                FETCH FIRST :top_k ROWS ONLY
                """,
                {
                    "query_embedding": embedding_array,
                    "min_threshold": VECTOR_SEARCH_CONFIG["min_vector_threshold"],
                    "top_k": VECTOR_SEARCH_CONFIG["final_top_k"],
                },
            )

            results = await cursor.fetchall()

            filtered_results = [
                (row[0], row[2], row[1])
                for row in results
                if row[2] >= INTENT_THRESHOLDS.get(row[0], 0.70)
            ]

            logger.info(
                "vector_search_results",
                query=query,
                total_results=len(results),
                filtered_results=len(filtered_results),
                top_match=filtered_results[0] if filtered_results else None,
            )

            return filtered_results, embedding_cache_hit

    async def route_intent_single(self, query: str, query_embedding: list[float] | None = None) -> tuple[str, float, str, bool]:
        """Route to single best intent with fallback to GENERAL_CONVERSATION."""
        results, embedding_cache_hit = await self.route_intent(query, query_embedding)

        if results:
            return (*results[0], embedding_cache_hit)
        return "GENERAL_CONVERSATION", 0.0, "", embedding_cache_hit

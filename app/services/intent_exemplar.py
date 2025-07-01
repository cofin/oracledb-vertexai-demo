from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.db.repositories.intent_exemplar import IntentExemplarRepository
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class IntentExemplarService:
    """Service for managing intent exemplar embeddings using a repository."""

    def __init__(self, intent_exemplar_repository: IntentExemplarRepository):
        """Initialize with intent exemplar repository."""
        self.repository = intent_exemplar_repository

    async def get_exemplars_with_phrases(self) -> dict[str, list[tuple[str, list[float]]]]:
        """Get all exemplars with their phrases and embeddings."""
        exemplars = await self.repository.get_exemplars_with_phrases()
        result: dict[str, list[tuple[str, list[float]]]] = {}
        for exemplar in exemplars:
            if exemplar.embedding:
                if exemplar.intent not in result:
                    result[exemplar.intent] = []
                result[exemplar.intent].append((exemplar.phrase, exemplar.embedding))
        return result

    async def cache_exemplar(
        self,
        intent: str,
        phrase: str,
        embedding: list[float],
    ) -> None:
        """Cache a single exemplar embedding."""
        await self.repository.cache_exemplar(intent, phrase, embedding)

    async def populate_cache(
        self,
        exemplars: dict[str, list[str]],
        vertex_ai_service: VertexAIService,
    ) -> int:
        """Populate cache with all exemplars. Returns count of embeddings created."""
        count = 0
        cached_exemplars = await self.get_exemplars_with_phrases()
        for intent, phrases in exemplars.items():
            for phrase in phrases:
                is_cached = any(p == phrase for p, _ in cached_exemplars.get(intent, []))
                if not is_cached:
                    embedding = await vertex_ai_service.create_embedding(phrase)
                    await self.cache_exemplar(intent, phrase, embedding)
                    count += 1
                    if count % 10 == 0:
                        logger.info("Cached %d exemplar embeddings...", count)
        logger.info("Populated cache with %d new exemplar embeddings", count)
        return count

"""Service for managing cached intent exemplar embeddings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import structlog
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from app.db import models

if TYPE_CHECKING:
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class IntentExemplarService(SQLAlchemyAsyncRepositoryService[models.IntentExemplar]):
    """Service for managing intent exemplar embeddings."""

    class Repo(SQLAlchemyAsyncRepository[models.IntentExemplar]):
        """Intent exemplar repository."""

        model_type = models.IntentExemplar

    repository_type = Repo

    def __init__(self, **repo_kwargs: Any) -> None:
        """Initialize with custom repository options."""
        super().__init__(**repo_kwargs)

    async def load_all_exemplars(self) -> dict[str, np.ndarray]:
        """Load all cached exemplar embeddings grouped by intent."""
        exemplars = await self.list()

        result: dict[str, list[list[float]]] = {}
        for exemplar in exemplars:
            if exemplar.embedding:
                # Convert from list to numpy array
                if exemplar.intent not in result:
                    result[exemplar.intent] = []
                result[exemplar.intent].append(exemplar.embedding)

        # Convert lists to numpy arrays
        numpy_result: dict[str, np.ndarray] = {}
        for intent, embeddings_list in result.items():
            numpy_result[intent] = np.array(embeddings_list)

        return numpy_result

    async def cache_exemplar(
        self,
        intent: str,
        phrase: str,
        embedding: list[float],
    ) -> models.IntentExemplar:
        """Cache a single exemplar embedding."""
        obj, _inserted = await self.get_or_upsert(
            intent=intent, phrase=phrase, embedding=embedding, match_fields=["intent", "phrase"]
        )
        return obj

    async def populate_cache(
        self,
        exemplars: dict[str, list[str]],
        vertex_ai_service: VertexAIService,
    ) -> int:
        """Populate cache with all exemplars. Returns count of embeddings created."""
        count = 0

        for intent, phrases in exemplars.items():
            for phrase in phrases:
                # Check if already cached
                existing = await self.repository.get_one_or_none(
                    intent=intent,
                    phrase=phrase,
                )

                if not existing or not existing.embedding:
                    # Generate embedding
                    embedding = await vertex_ai_service.create_embedding(phrase)
                    await self.cache_exemplar(intent, phrase, embedding)
                    count += 1

                    if count % 10 == 0:
                        logger.info("Cached %d exemplar embeddings...", count)

        logger.info("Populated cache with %d new exemplar embeddings", count)
        return count

    async def get_exemplars_with_phrases(self) -> dict[str, list[tuple[str, list[float]]]]:
        """Get all exemplars with their phrases and embeddings."""
        exemplars = await self.list()

        result: dict[str, list[tuple[str, list[float]]]] = {}
        for exemplar in exemplars:
            if exemplar.embedding:
                if exemplar.intent not in result:
                    result[exemplar.intent] = []
                result[exemplar.intent].append((exemplar.phrase, exemplar.embedding))

        return result

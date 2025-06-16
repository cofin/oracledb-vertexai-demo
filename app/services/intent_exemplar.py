"""Service for managing cached intent exemplar embeddings."""

from __future__ import annotations

import array
from typing import TYPE_CHECKING

import numpy as np
import structlog

from app.services.base import BaseService

if TYPE_CHECKING:
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class IntentExemplarService(BaseService):
    """Service for managing intent exemplar embeddings using raw Oracle SQL."""

    async def get_exemplars_with_phrases(self) -> dict[str, list[tuple[str, list[float]]]]:
        """Get all exemplars with their phrases and embeddings."""
        async with self.get_cursor() as cursor:
            await cursor.execute("""
                SELECT intent, phrase, embedding
                FROM intent_exemplar
                WHERE embedding IS NOT NULL
                ORDER BY intent, phrase
            """)

            result: dict[str, list[tuple[str, list[float]]]] = {}
            async for row in cursor:
                intent, phrase, embedding_vector = row
                if embedding_vector:
                    # Convert Oracle VECTOR to Python list
                    embedding = list(embedding_vector)
                    if intent not in result:
                        result[intent] = []
                    result[intent].append((phrase, embedding))

            return result

    async def load_all_exemplars(self) -> dict[str, np.ndarray]:
        """Load all cached exemplar embeddings grouped by intent."""
        async with self.get_cursor() as cursor:
            await cursor.execute("""
                SELECT intent, embedding
                FROM intent_exemplar
                WHERE embedding IS NOT NULL
                ORDER BY intent
            """)

            result: dict[str, list[list[float]]] = {}
            async for row in cursor:
                intent, embedding_vector = row
                if embedding_vector:
                    # Convert Oracle VECTOR to Python list
                    embedding = list(embedding_vector)
                    if intent not in result:
                        result[intent] = []
                    result[intent].append(embedding)

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
    ) -> None:
        """Cache a single exemplar embedding."""
        async with self.get_cursor() as cursor:
            # Convert Python list to Oracle VECTOR format
            oracle_vector = array.array("f", embedding)

            await cursor.execute(
                """
                MERGE INTO intent_exemplar ie
                USING (SELECT :intent AS intent, :phrase AS phrase FROM dual) src
                ON (ie.intent = src.intent AND ie.phrase = src.phrase)
                WHEN MATCHED THEN
                    UPDATE SET
                        embedding = :embedding
                WHEN NOT MATCHED THEN
                    INSERT (intent, phrase, embedding)
                    VALUES (:intent2, :phrase2, :embedding2)
                """,
                {
                    "intent": intent,
                    "phrase": phrase,
                    "embedding": oracle_vector,
                    "intent2": intent,
                    "phrase2": phrase,
                    "embedding2": oracle_vector,
                },
            )

            await self.connection.commit()

    async def populate_cache(
        self,
        exemplars: dict[str, list[str]],
        vertex_ai_service: VertexAIService,
    ) -> int:
        """Populate cache with all exemplars. Returns count of embeddings created."""
        count = 0

        async with self.get_cursor() as cursor:
            for intent, phrases in exemplars.items():
                for phrase in phrases:
                    # Check if already cached
                    await cursor.execute(
                        """
                        SELECT embedding FROM intent_exemplar
                        WHERE intent = :intent AND phrase = :phrase
                    """,
                        {"intent": intent, "phrase": phrase},
                    )

                    result = await cursor.fetchone()

                    if not result or not result[0]:
                        # Generate embedding
                        embedding = await vertex_ai_service.create_embedding(phrase)
                        await self.cache_exemplar(intent, phrase, embedding)
                        count += 1

                        if count % 10 == 0:
                            logger.info("Cached %d exemplar embeddings...", count)

            logger.info("Populated cache with %d new exemplar embeddings", count)
            return count

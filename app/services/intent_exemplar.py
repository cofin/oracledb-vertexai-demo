"""Service for managing cached intent exemplar embeddings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
import structlog
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from app.db import models

if TYPE_CHECKING:
    import oracledb

    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class IntentExemplarServiceProtocol(Protocol):
    """Protocol for intent exemplar services."""

    async def get_exemplars_with_phrases(self) -> dict[str, list[tuple[str, list[float]]]]:
        """Get all exemplars with their phrases and embeddings."""
        ...

    async def load_all_exemplars(self) -> dict[str, np.ndarray]:
        """Load all cached exemplar embeddings grouped by intent."""
        ...

    async def populate_cache(
        self,
        exemplars: dict[str, list[str]],
        vertex_ai_service: VertexAIService,
    ) -> int:
        """Populate cache with all exemplars. Returns count of embeddings created."""
        ...


class IntentExemplarService(SQLAlchemyAsyncRepositoryService[models.IntentExemplar]):
    """Service for managing intent exemplar embeddings using SQLAlchemy."""

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


class RawIntentExemplarService:
    """Service for managing intent exemplar embeddings using raw Oracle SQL."""

    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        """Initialize with Oracle connection."""
        self.connection = connection

    async def get_exemplars_with_phrases(self) -> dict[str, list[tuple[str, list[float]]]]:
        """Get all exemplars with their phrases and embeddings."""
        cursor = self.connection.cursor()
        try:
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
        finally:
            cursor.close()

    async def load_all_exemplars(self) -> dict[str, np.ndarray]:
        """Load all cached exemplar embeddings grouped by intent."""
        cursor = self.connection.cursor()
        try:
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
        finally:
            cursor.close()

    async def cache_exemplar(
        self,
        intent: str,
        phrase: str,
        embedding: list[float],
    ) -> None:
        """Cache a single exemplar embedding."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                MERGE INTO intent_exemplar ie
                USING (SELECT :intent AS intent, :phrase AS phrase FROM dual) src
                ON (ie.intent = src.intent AND ie.phrase = src.phrase)
                WHEN MATCHED THEN
                    UPDATE SET
                        embedding = :embedding,
                        updated_at = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (intent, phrase, embedding)
                    VALUES (:intent2, :phrase2, :embedding2)
                """,
                {
                    "intent": intent,
                    "phrase": phrase,
                    "embedding": embedding,
                    "intent2": intent,
                    "phrase2": phrase,
                    "embedding2": embedding,
                },
            )

            await self.connection.commit()
        finally:
            cursor.close()

    async def populate_cache(
        self,
        exemplars: dict[str, list[str]],
        vertex_ai_service: VertexAIService,
    ) -> int:
        """Populate cache with all exemplars. Returns count of embeddings created."""
        count = 0
        cursor = self.connection.cursor()

        try:
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
        finally:
            cursor.close()

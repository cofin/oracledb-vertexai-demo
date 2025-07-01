from app.schemas import IntentExemplarDTO
from .base import BaseRepository

class IntentExemplarRepository(BaseRepository[IntentExemplarDTO]):
    def __init__(self, connection):
        super().__init__(connection, IntentExemplarDTO)

    async def get_exemplars_with_phrases(self) -> list[IntentExemplarDTO]:
        query = "SELECT id, intent, phrase, embedding, created_at, updated_at FROM intent_exemplar WHERE embedding IS NOT NULL ORDER BY intent, phrase"
        return await self.fetch_all(query)

    async def cache_exemplar(self, intent: str, phrase: str, embedding: list[float]) -> None:
        import array
        oracle_vector = array.array("f", embedding)
        query = """
            MERGE INTO intent_exemplar ie
            USING (SELECT :intent AS intent, :phrase AS phrase FROM dual) src
            ON (ie.intent = src.intent AND ie.phrase = src.phrase)
            WHEN MATCHED THEN
                UPDATE SET
                    embedding = :embedding
            WHEN NOT MATCHED THEN
                INSERT (intent, phrase, embedding)
                VALUES (:intent2, :phrase2, :embedding2)
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
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

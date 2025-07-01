from typing import Any, Generic, TypeVar
import oracledb
from app.lib.schema import BaseStruct

T = TypeVar("T", bound=BaseStruct)

class BaseRepository(Generic[T]):
    """A generic repository providing robust row-to-model mapping."""
    def __init__(self, connection: oracledb.AsyncConnection, model: type[T]):
        self.connection = connection
        self.model = model

    async def _map_row_to_model(self, cursor: oracledb.AsyncCursor, row: tuple) -> T:
        """Dynamically maps a single database row to a msgspec model."""
        column_names = [desc[0].lower() for desc in cursor.description]
        row_dict = dict(zip(column_names, row))
        return self.model(**row_dict)

    async def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> T | None:
        """Execute a query and fetch a single model instance."""
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params or {})
            row = await cursor.fetchone()
            if row is None:
                return None
            return await self._map_row_to_model(cursor, row)

    async def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[T]:
        """Execute a query and fetch all model instances."""
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params or {})
            return [await self._map_row_to_model(cursor, row) async for row in cursor]

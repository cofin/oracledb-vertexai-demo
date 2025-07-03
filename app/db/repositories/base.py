from typing import Any, Generic, TypeVar

import oracledb
import structlog

from app.lib.exceptions import DatabaseConnectionError, RepositoryError
from app.lib.schema import BaseStruct

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseStruct)

class BaseRepository(Generic[T]):
    """A generic repository providing robust row-to-model mapping."""
    def __init__(self, connection: oracledb.AsyncConnection, model: type[T]) -> None:
        self.connection = connection
        self.model = model

    async def _map_row_to_model(self, cursor: oracledb.AsyncCursor, row: tuple) -> T:
        """Dynamically maps a single database row to a msgspec model."""
        try:
            column_names = [desc[0].lower() for desc in cursor.description]
            row_dict = dict(zip(column_names, row, strict=False))
            return self.model(**row_dict)
        except Exception as e:
            logger.exception("Failed to map row to model",
                        model=self.model.__name__,
                        error=str(e),
                        exc_info=e)
            msg = f"Failed to map database row to {self.model.__name__}"
            raise RepositoryError(msg) from e

    async def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> T | None:
        """Execute a query and fetch a single model instance."""
        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, params or {})
                row = await cursor.fetchone()
                if row is None:
                    return None
                return await self._map_row_to_model(cursor, row)
        except oracledb.InterfaceError as e:
            logger.exception("Database connection error", query=query, exc_info=e)
            msg = "Lost database connection"
            raise DatabaseConnectionError(msg) from e
        except oracledb.Error as e:
            logger.exception("Database query failed", query=query, params=params, exc_info=e)
            msg = "Failed to fetch record from database"
            raise RepositoryError(msg) from e
        except Exception as e:
            logger.exception("Unexpected error in fetch_one", query=query, exc_info=e)
            msg = "An unexpected error occurred"
            raise RepositoryError(msg) from e

    async def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[T]:
        """Execute a query and fetch all model instances."""
        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, params or {})
                return [await self._map_row_to_model(cursor, row) async for row in cursor]
        except oracledb.InterfaceError as e:
            logger.exception("Database connection error", query=query, exc_info=e)
            msg = "Lost database connection"
            raise DatabaseConnectionError(msg) from e
        except oracledb.Error as e:
            logger.exception("Database query failed", query=query, params=params, exc_info=e)
            msg = "Failed to fetch records from database"
            raise RepositoryError(msg) from e
        except Exception as e:
            logger.exception("Unexpected error in fetch_all", query=query, exc_info=e)
            msg = "An unexpected error occurred"
            raise RepositoryError(msg) from e

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> None:
        """Execute a query without fetching results (for INSERT, UPDATE, DELETE)."""
        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, params or {})
        except oracledb.InterfaceError as e:
            logger.exception("Database connection error", query=query, exc_info=e)
            msg = "Lost database connection"
            raise DatabaseConnectionError(msg) from e
        except oracledb.Error as e:
            logger.exception("Database query failed", query=query, params=params, exc_info=e)
            msg = "Failed to execute query"
            raise RepositoryError(msg) from e
        except Exception as e:
            logger.exception("Unexpected error in execute", query=query, exc_info=e)
            msg = "An unexpected error occurred"
            raise RepositoryError(msg) from e

    async def execute_many(self, query: str, params_list: list[dict[str, Any]]) -> None:
        """Execute a query multiple times with different parameters."""
        try:
            async with self.connection.cursor() as cursor:
                await cursor.executemany(query, params_list)
        except oracledb.InterfaceError as e:
            logger.exception("Database connection error", query=query, exc_info=e)
            msg = "Lost database connection"
            raise DatabaseConnectionError(msg) from e
        except oracledb.Error as e:
            logger.exception("Database query failed", query=query, exc_info=e)
            msg = "Failed to execute batch query"
            raise RepositoryError(msg) from e
        except Exception as e:
            logger.exception("Unexpected error in execute_many", query=query, exc_info=e)
            msg = "An unexpected error occurred"
            raise RepositoryError(msg) from e

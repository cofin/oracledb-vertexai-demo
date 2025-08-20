"""Unit of Work pattern for managing database transactions."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Self

import structlog

from app.lib.exceptions import RepositoryError

if TYPE_CHECKING:
    from types import TracebackType

    import oracledb

logger = structlog.get_logger(__name__)


class UnitOfWork:
    """Manages database transactions across multiple repositories."""

    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        self.connection = connection
        self._in_transaction = False

    async def __aenter__(self) -> Self:
        """Begin a transaction."""
        try:
            # Oracle starts transactions automatically with the first DML statement
            # But we track the state for proper cleanup
            self._in_transaction = True
            logger.debug("Starting unit of work transaction")
        except Exception as e:
            logger.exception("Failed to start transaction", exc_info=e)
            msg = "Failed to start transaction"
            raise RepositoryError(msg) from e
        else:
            return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Commit or rollback the transaction based on exceptions."""
        if not self._in_transaction:
            return

        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        except Exception as e:
            logger.exception("Error during transaction cleanup", exc_info=e)
            # Try to rollback if commit failed
            if exc_type is None:
                with contextlib.suppress(Exception):
                    await self.rollback()
            msg = "Transaction cleanup failed"
            raise RepositoryError(msg) from e
        finally:
            self._in_transaction = False

    async def commit(self) -> None:
        """Commit the current transaction."""
        try:
            await self.connection.commit()
            logger.debug("Transaction committed")
        except Exception as e:
            logger.exception("Failed to commit transaction", exc_info=e)
            msg = "Failed to commit transaction"
            raise RepositoryError(msg) from e

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        try:
            await self.connection.rollback()
            logger.debug("Transaction rolled back")
        except Exception as e:
            logger.exception("Failed to rollback transaction", exc_info=e)
            msg = "Failed to rollback transaction"
            raise RepositoryError(msg) from e

    def get_connection(self) -> oracledb.AsyncConnection:
        """Get the connection for creating repositories."""
        return self.connection

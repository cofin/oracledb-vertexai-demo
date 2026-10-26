# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle 26ai async service bases, SQLFileLoader factory, and filter pagination facade."""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, cast

from sqlspec.adapters.oracledb import OracleAsyncConfig, OracleAsyncDriver
from sqlspec.core.filters import FilterTypes, OffsetPagination
from sqlspec.extensions.litestar.providers import create_filter_dependencies
from sqlspec.loader import SQLFileLoader
from sqlspec.service import SQLSpecAsyncService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Sequence

__all__ = (
    "FilterTypes",
    "OffsetPagination",
    "OracleAsyncService",
    "OracleLoaderService",
    "create_filter_dependencies",
    "default_sql_loader",
)


@lru_cache(maxsize=1)
def default_sql_loader() -> SQLFileLoader:
    """Load and cache named SQL queries from ``src/app/db/sql``."""
    sql_dir = Path(__file__).resolve().parents[1] / "db" / "sql"
    loader = SQLFileLoader()
    loader.load_sql(sql_dir)
    return loader


class OracleAsyncService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Oracle 26ai async data service supporting request drivers or app-scoped configs."""

    __slots__ = ()

    def __init__(self, driver: OracleAsyncDriver) -> None:
        """Initialize the service with a request-scoped OracleAsyncDriver."""
        super().__init__(driver)

    @classmethod
    def from_config(cls, config: OracleAsyncConfig, *, loader: SQLFileLoader | None = None) -> Self:
        """Construct an app-scoped service backed by an OracleAsyncConfig connection pool."""
        instance = cls.__new__(cls)
        instance._init_from_config(config, loader)
        return instance

    @asynccontextmanager
    async def provide_app_session(self) -> AsyncGenerator[OracleAsyncDriver, None]:
        """Yield an OracleAsyncDriver from either the bound session or the app-scoped pool."""
        async with self.provide_session() as session:
            yield session

    async def execute_many(self, statement: Any, parameters: Sequence[Any], *, auto_commit: bool = False) -> Any:
        """Execute a batch DML statement across parameter sets and optionally commit."""
        async with self.provide_app_session() as session:
            result = await session.execute_many(statement, parameters)
            if auto_commit:
                await session.commit()
            return result

    def _init_from_driver(self, driver: OracleAsyncDriver, loader: SQLFileLoader | None) -> None:
        """Initialize the underlying SQLSpecAsyncService with a request-scoped driver."""
        super().__init__(driver, loader=loader)

    def _init_from_config(self, config: OracleAsyncConfig, loader: SQLFileLoader | None) -> None:
        """Initialize the underlying SQLSpecAsyncService with an app-scoped pool config."""
        super().__init__(config=config, loader=loader)


class OracleLoaderService(OracleAsyncService):
    """Oracle async service with an attached SQLFileLoader for named SQL lookup."""

    __slots__ = ()

    def __init__(self, driver: OracleAsyncDriver, loader: SQLFileLoader = cast("SQLFileLoader", None)) -> None:
        """Initialize with a request-scoped driver and default to ``default_sql_loader()``."""
        self._init_from_driver(driver, loader or default_sql_loader())

    @classmethod
    def from_config(cls, config: OracleAsyncConfig, *, loader: SQLFileLoader | None = None) -> Self:
        """Construct an app-scoped loader service backed by an OracleAsyncConfig connection pool."""
        instance = cls.__new__(cls)
        instance._init_from_config(config, loader or default_sql_loader())
        return instance

    def get_sql(self, name: str) -> Any:
        """Retrieve a named SQL statement from the attached SQLFileLoader."""
        if self._loader is None:
            return default_sql_loader().get_sql(name)
        return self._loader.get_sql(name)

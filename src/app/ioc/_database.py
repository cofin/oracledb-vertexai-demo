# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka provider for Oracle persistence."""

import sys
from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlspec.adapters.oracledb import OracleAsyncConfig, OracleAsyncDriver

from app import config

__all__ = (
    "DBProvider",
    "LitestarPersistenceProvider",
)


class DBProvider(Provider):
    """Oracle config (APP) and per-request driver (REQUEST)."""

    @provide(scope=Scope.APP)
    def provide_config(self) -> OracleAsyncConfig:
        """Provide the APP-scoped OracleAsyncConfig."""
        return config.db

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterator[OracleAsyncDriver]:
        """Provide per-request OracleAsyncDriver."""
        session_context = config.db_manager.provide_session(config.db)
        driver = await session_context.__aenter__()
        try:
            yield driver
        except BaseException:
            await session_context.__aexit__(*sys.exc_info())
            raise
        else:
            await session_context.__aexit__(None, None, None)


LitestarPersistenceProvider = DBProvider

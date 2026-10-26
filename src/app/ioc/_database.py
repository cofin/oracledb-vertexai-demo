# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka provider for Oracle persistence."""

import sys
from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from litestar_queues import QueuePlugin, QueueService
from sqlspec.adapters.oracledb import OracleAsyncConfig, OracleAsyncDriver

from app.lib.settings import DatabaseSettings, QueueSettings

__all__ = ("DBProvider",)


class DBProvider(Provider):
    """Oracle config (APP), queue service (APP), and per-request driver (REQUEST)."""

    def __init__(
        self,
        *,
        db_config: OracleAsyncConfig | None = None,
        queue_config: OracleAsyncConfig | None = None,
        queue_plugin: QueuePlugin | None = None,
    ) -> None:
        super().__init__()
        self._db_config = db_config
        self._queue_config = queue_config
        self._queue_plugin = queue_plugin

    @provide(scope=Scope.APP)
    def provide_config(self, db_settings: DatabaseSettings) -> OracleAsyncConfig:
        """Provide the APP-scoped OracleAsyncConfig."""
        if self._db_config is not None:
            return self._db_config
        return db_settings.get_config()

    @provide(scope=Scope.APP)
    async def provide_queue_service(
        self, db_settings: DatabaseSettings, queue_settings: QueueSettings
    ) -> AsyncIterator[QueueService]:
        """Provide the APP-scoped QueueService, sharing the ASGI QueuePlugin when supplied."""
        if self._queue_plugin is not None:
            active_service = getattr(self._queue_plugin, "_service", None)
            if active_service is not None:
                yield active_service
                return
            service = self._queue_plugin.get_service()
            await service.open()
            try:
                yield service
            finally:
                await service.close()
            return

        q_db = self._queue_config if self._queue_config is not None else db_settings.get_queue_config()
        plugin = QueuePlugin(config=queue_settings.get_config(q_db))
        service = plugin.get_service()
        await service.open()
        try:
            yield service
        finally:
            await service.close()

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self, db_config: OracleAsyncConfig) -> AsyncIterator[OracleAsyncDriver]:
        """Provide per-request OracleAsyncDriver."""
        session_context = db_config.provide_session()
        driver = await session_context.__aenter__()
        try:
            yield driver
        except BaseException:
            await session_context.__aexit__(*sys.exc_info())
            raise
        else:
            await session_context.__aexit__(None, None, None)

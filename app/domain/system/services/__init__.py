from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from sqlspec.adapters.oracledb import OracleAsyncConfig
from sqlspec.base import SQLSpec
from sqlspec.driver import AsyncDriverAdapterBase

from app.config import db, db_manager

from ._cache import CacheService
from ._exemplar import ExemplarService
from ._metrics import MetricsService
from ._persona_manager import PersonaManager


class SystemServiceProvider(Provider):
    scope = Scope.REQUEST

    @provide(scope=Scope.APP)
    def get_sqlspec_manager(self) -> SQLSpec:
        return db_manager

    @provide(scope=Scope.APP)
    def get_database_config(self) -> OracleAsyncConfig:
        return db

    @provide(scope=Scope.REQUEST)
    async def get_db_session(
        self,
        manager: SQLSpec,
        config: OracleAsyncConfig,
    ) -> AsyncIterable[AsyncDriverAdapterBase]:
        async with manager.provide_session(config) as session:
            yield session

    cache_service = provide(CacheService)
    exemplar_service = provide(ExemplarService)
    metrics_service = provide(MetricsService)
    persona_manager = provide(PersonaManager, scope=Scope.APP)

__all__ = (
    "CacheService",
    "ExemplarService",
    "MetricsService",
    "PersonaManager",
    "SystemServiceProvider",
)

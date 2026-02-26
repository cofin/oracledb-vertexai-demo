"""Dishka container configuration for Litestar."""

from collections.abc import AsyncIterator

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from sqlspec.driver import AsyncDriverAdapterBase

from app.config import db, db_manager
from app.domain.chat.services import ChatServiceProvider
from app.domain.products.services import ProductsServiceProvider
from app.domain.system.services import SystemServiceProvider
from app.lib.di import LitestarProvider


class LitestarPersistenceProvider(Provider):
    """Persistence provider for Litestar requests."""

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterator[AsyncDriverAdapterBase]:
        """Provide a fresh database driver for each request scope."""
        async with db_manager.provide_session(db) as driver:
            yield driver


def make_litestar_container() -> AsyncContainer:
    """Create the Dishka container for Litestar."""
    return make_async_container(
        LitestarProvider(),
        LitestarPersistenceProvider(),
        SystemServiceProvider(),
        ProductsServiceProvider(),
        ChatServiceProvider(),
    )


__all__ = ("LitestarPersistenceProvider", "make_litestar_container")

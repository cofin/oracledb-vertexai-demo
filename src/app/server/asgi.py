# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ASGI application factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar import Litestar

__all__ = ("app", "create_app")

app: Litestar


def create_app() -> Litestar:
    """Create and configure the Litestar ASGI application."""
    from contextlib import asynccontextmanager

    from litestar import Litestar

    from app.ioc import make_container
    from app.lib.di import LitestarProvider, setup_dishka
    from app.lib.settings import get_settings
    from app.server.core import ApplicationCore

    settings = get_settings()
    container = make_container(LitestarProvider())

    @asynccontextmanager
    async def dishka_lifespan(litestar_app: Litestar) -> AsyncGenerator[None, None]:
        del litestar_app
        try:
            yield
        finally:
            await container.close()

    litestar_app = Litestar(debug=settings.app.DEBUG, plugins=[ApplicationCore()], lifespan=[dishka_lifespan])
    setup_dishka(container, litestar_app)
    return litestar_app


def __getattr__(name: str) -> object:
    """Lazily instantiate the module-level app attribute on first access."""
    if name == "app":
        instance = create_app()
        globals()["app"] = instance
        return instance
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)

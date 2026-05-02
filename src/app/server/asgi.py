# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar import Litestar


def create_app() -> Litestar:
    """Create ASGI application."""
    from contextlib import asynccontextmanager

    from litestar import Litestar

    from app.ioc import make_container
    from app.lib.di import LitestarProvider, setup_dishka
    from app.lib.settings import get_settings
    from app.server.core import ApplicationCore

    settings = get_settings()
    container = make_container(LitestarProvider())

    @asynccontextmanager
    async def dishka_lifespan(app: Litestar) -> AsyncIterator[None]:
        yield
        await container.close()

    app = Litestar(
        debug=settings.app.DEBUG,
        plugins=[ApplicationCore()],
        lifespan=[dishka_lifespan],
    )
    setup_dishka(container, app)
    return app


app = create_app()

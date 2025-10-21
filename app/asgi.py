# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.adk.monkey_patches import apply_genai_client_patch

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar import Litestar

apply_genai_client_patch()


def create_app() -> Litestar:
    """Create ASGI application."""

    from contextlib import asynccontextmanager

    from dishka import make_async_container
    from litestar import Litestar

    from app.lib.di import setup_dishka
    from app.lib.settings import get_settings
    from app.server import plugins
    from app.server.providers import ADKProvider, CoreServiceProvider, SQLSpecProvider

    settings = get_settings()

    # Create Dishka container with all providers
    container = make_async_container(
        SQLSpecProvider(),
        CoreServiceProvider(),
        ADKProvider(),
    )

    # Make container available to ADK tools
    from app.services.adk.tools import set_app_container

    set_app_container(container)

    @asynccontextmanager
    async def dishka_lifespan(app: Litestar) -> AsyncIterator[None]:
        """Manage Dishka container lifecycle."""
        yield
        await container.close()

    # Create app with Dishka integration
    app = Litestar(
        debug=settings.app.DEBUG,
        plugins=[plugins.app_config],
        lifespan=[dishka_lifespan],
    )

    # Setup Dishka integration with Litestar
    setup_dishka(container, app)

    return app


app = create_app()

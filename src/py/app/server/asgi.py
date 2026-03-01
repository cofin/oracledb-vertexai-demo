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

from app.domain.chat.services.adk import (
    apply_genai_client_patch,  # Note: Need to move patch if it was in monkey_patches
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar import Litestar

# Temporary fix: ensure apply_genai_client_patch exists or move logic
try:
    from app.domain.chat.services.adk import apply_genai_client_patch
    apply_genai_client_patch()
except ImportError:
    pass


def create_app() -> Litestar:
    """Create ASGI application."""
    from contextlib import asynccontextmanager

    from litestar import Litestar

    from app.ioc import make_litestar_container
    from app.lib.di import setup_dishka
    from app.lib.settings import get_settings
    from app.server.core import ApplicationCore

    settings = get_settings()
    container = make_litestar_container()

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

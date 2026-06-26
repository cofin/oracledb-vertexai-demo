# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Page-level routes for the HTMX frontend.

HTMX-aware partials live alongside the domain controllers that own
their data (e.g. ``app.domain.chat.controllers``,
``app.domain.products.controllers``).
"""

from typing import Annotated

import structlog
from litestar import Controller, get
from litestar.params import QueryParameter
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate

from app.domain.chat.services import ADKRunner
from app.domain.chat.session import adk_session_identity
from app.domain.products.services import StoreService
from app.lib.di import Inject

logger = structlog.get_logger()


class PageController(Controller):
    """Server-rendered page routes for chat and explore."""

    @get(path="/", name="pages.chat", exclude_from_auth=True, include_in_schema=False)
    async def chat_page(self, request: HTMXRequest, adk_runner: Inject[ADKRunner]) -> HTMXTemplate:
        user_id, session_id = adk_session_identity(request)
        history_messages = await adk_runner.get_history_or_empty(user_id=user_id, session_id=session_id)
        return HTMXTemplate(template_name="pages/chat.html.j2", context={"history_messages": history_messages})

    @get(path="/explore", name="pages.explore", exclude_from_auth=True, include_in_schema=False)
    async def explore_page(
        self,
        stores_service: Inject[StoreService],
        search_query: Annotated[str | None, QueryParameter(name="query")] = None,
    ) -> HTMXTemplate:

        try:
            stores = await stores_service.get_all_stores()
        except Exception as exc:  # noqa: BLE001
            await logger.awarning("Store inventory selector unavailable", error_type=type(exc).__name__)
            stores = []
        return HTMXTemplate(
            template_name="pages/explore.html.j2", context={"query": search_query or "", "stores": stores}
        )

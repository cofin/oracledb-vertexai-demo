# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Page-level routes for the HTMX frontend."""

from typing import Annotated

import structlog
from litestar import get
from litestar.params import QueryParameter
from litestar.response import Template
from litestar_htmx import HTMXRequest
from litestar_security import PublicController

from app.domain.ai.services import AgentOrchestrationService
from app.domain.chat.session import chat_session_identity
from app.domain.products.services import StoreService
from app.lib.di import Inject

__all__ = ("PageController",)

logger = structlog.get_logger()


class PageController(PublicController):
    """Server-rendered page routes for chat and explore."""

    @get(path="/", name="pages.chat", include_in_schema=False)
    async def chat_page(self, request: HTMXRequest, orchestrator: Inject[AgentOrchestrationService]) -> Template:
        """Render the primary coffee chat landing page with session history.

        Args:
            request: Active HTMX request.
            orchestrator: Injected agent orchestration service.

        Returns:
            Rendered Jinja template for chat page.
        """
        user_id, session_id = chat_session_identity(request)
        try:
            history_messages = await orchestrator.get_display_history(session_id=session_id, user_id=user_id)
        except Exception as exc:
            await logger.awarning("Chat history retrieval failed", error_type=type(exc).__name__)
            history_messages = []
        return Template(template_name="pages/chat.html.j2", context={"history_messages": history_messages})

    @get(path="/explore", name="pages.explore", include_in_schema=False)
    async def explore_page(
        self,
        stores_service: Inject[StoreService],
        search_query: Annotated[str | None, QueryParameter(name="query")] = None,
    ) -> Template:
        """Render the explore and vector search page.

        Args:
            stores_service: Injected store service.
            search_query: Optional search query parameter.

        Returns:
            Rendered Jinja template for explore page.
        """
        try:
            stores = await stores_service.get_all_stores()
        except Exception as exc:
            await logger.awarning("Store inventory selector unavailable", error_type=type(exc).__name__)
            stores = []
        return Template(template_name="pages/explore.html.j2", context={"query": search_query or "", "stores": stores})

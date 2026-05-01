# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Page-level routes for the HTMX frontend.

HTMX-aware partials live alongside the domain controllers that own
their data (e.g. ``app.domain.chat.controllers``,
``app.domain.products.controllers``).
"""

import structlog
from litestar import Controller, get
from litestar.plugins.htmx import HTMXRequest
from litestar.response import Template

from app.domain.chat.services import ADKRunner
from app.domain.chat.session import adk_session_identity
from app.lib.di import Inject

logger = structlog.get_logger()


class PageController(Controller):
    """Server-rendered page routes for chat and explore."""

    @get(path="/", name="pages.chat", exclude_from_auth=True, include_in_schema=False)
    async def chat_page(self, request: HTMXRequest, adk_runner: Inject[ADKRunner]) -> Template:
        history_messages = []
        try:
            user_id, session_id = adk_session_identity(request)
            history_messages = await adk_runner.get_history(user_id=user_id, session_id=session_id)
        except Exception as exc:  # noqa: BLE001
            await logger.awarning("Chat history unavailable", error_type=type(exc).__name__)
        return Template(template_name="pages/chat.html.j2", context={"history_messages": history_messages})

    @get(path="/explore", name="pages.explore", exclude_from_auth=True, include_in_schema=False)
    async def explore_page(self, q: str | None = None) -> Template:
        return Template(template_name="pages/explore.html.j2", context={"query": q or ""})

# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Page-level routes for the HTMX frontend.

HTMX-aware partials live alongside the domain controllers that own
their data (e.g. ``app.domain.chat.controllers``,
``app.domain.products.controllers``).
"""

from litestar import Controller, get
from litestar.response import Template


class PageController(Controller):
    """Server-rendered page routes for chat and explore."""

    @get(path="/", name="pages.chat", exclude_from_auth=True, include_in_schema=False)
    async def chat_page(self) -> Template:
        return Template(template_name="pages/chat.html.j2")

    @get(path="/explore", name="pages.explore", exclude_from_auth=True, include_in_schema=False)
    async def explore_page(self) -> Template:
        return Template(template_name="pages/explore.html.j2")

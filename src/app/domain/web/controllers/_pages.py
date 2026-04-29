# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Page-level routes for the HTMX frontend.

Both pages render a Jinja template; HTMX-aware partials live alongside
domain controllers (e.g. ``app.domain.chat.controllers``).
"""

from litestar import Controller, get
from litestar.exceptions import NotFoundException
from litestar.response import Template


class PageController(Controller):
    """Server-rendered page routes for chat and explore."""

    @get(path="/", name="pages.chat", exclude_from_auth=True, include_in_schema=False)
    async def chat_page(self) -> Template:
        return Template(template_name="pages/chat.html.j2")

    @get(path="/explore", name="pages.explore", exclude_from_auth=True, include_in_schema=False)
    async def explore_page(self) -> Template:
        # Phase 5.4 swaps the placeholder for the real 5-panel template.
        raise NotFoundException(detail="Explore page lands in Phase 5.")

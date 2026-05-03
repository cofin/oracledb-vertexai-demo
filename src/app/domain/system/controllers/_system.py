# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from litestar import Controller, get
from litestar.response import File

from app.lib.settings import BASE_DIR


class SystemController(Controller):
    """System controller for root-level and un-grouped system routes."""

    @get(path="/favicon.ico", name="favicon", exclude_from_auth=True, include_in_schema=False)
    async def favicon(self) -> File:
        """Serve favicon with security headers."""
        return File(
            path=BASE_DIR.parents[1] / "src" / "resources" / "public" / "favicon.ico",
            media_type="image/x-icon",
            headers={"Cache-Control": "public, max-age=31536000", "X-Content-Type-Options": "nosniff"},
        )

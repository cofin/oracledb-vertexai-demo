# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""System controller for root-level and un-grouped system routes."""

from litestar import get
from litestar.response import File
from litestar_security import PublicController

from app.lib.settings import BASE_DIR


class SystemController(PublicController):
    """System controller for root-level and un-grouped system routes."""

    @get(path=["/health", "/api/system/health"], name="system.health")
    async def health(self) -> dict[str, str]:
        """Return lightweight liveness status for Cloud Run and local checks."""
        return {"status": "ok"}

    @get(path="/favicon.ico", name="favicon", include_in_schema=False)
    async def favicon(self) -> File:
        """Serve favicon with security headers."""
        return File(
            path=BASE_DIR.parents[1] / "src" / "resources" / "public" / "favicon.ico",
            media_type="image/x-icon",
            headers={"Cache-Control": "public, max-age=31536000", "X-Content-Type-Options": "nosniff"},
        )

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar import Litestar


def create_app() -> Litestar:
    """Create ASGI application."""

    from litestar import Litestar

    from app.lib.settings import get_settings
    from app.server import plugins

    settings = get_settings()

    return Litestar(debug=settings.app.DEBUG, plugins=[plugins.app_config])


app = create_app()

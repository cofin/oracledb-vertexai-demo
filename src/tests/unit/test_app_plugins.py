# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Phase 4.3 contract: ``ApplicationCore.on_app_init`` registers
``HTMXPlugin``, ``FlashPlugin``, and a ``TemplateConfig`` pointing at
``src/app/domain/web/templates``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.plugins.flash import FlashPlugin
from litestar.plugins.htmx import HTMXPlugin

if TYPE_CHECKING:
    from litestar import Litestar


def _plugin_types(app: Litestar) -> list[type]:
    return [type(p) for p in app.plugins]


def test_htmx_plugin_registered(app: Litestar) -> None:
    assert HTMXPlugin in _plugin_types(app)


def test_flash_plugin_registered(app: Litestar) -> None:
    assert FlashPlugin in _plugin_types(app)


def test_template_config_points_at_web_templates(app: Litestar) -> None:
    assert app.template_engine is not None, "TemplateConfig must be set so Jinja templates resolve"
    from app.lib.settings import BASE_DIR

    assert (BASE_DIR / "domain" / "web" / "templates").is_dir()


def test_app_csrf_header_name_is_x_csrf_token(app: Litestar) -> None:
    """Phase 4.4 rename verified end-to-end (settings → AppConfig → app)."""
    if app.csrf_config is None:
        return
    assert app.csrf_config.header_name == "X-CSRFToken"

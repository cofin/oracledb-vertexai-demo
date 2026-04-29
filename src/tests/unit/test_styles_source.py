# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Phase 3.3 contract: the Tailwind v4 styles source must declare its template
scan path or the build silently emits a CSS bundle missing utility classes
referenced from ``.html.j2`` files.

This test pins the two load-bearing directives:

* ``@import "tailwindcss"`` — switches Tailwind v4's CSS-first config on.
* ``@source "../app/domain/web/templates"`` — tells v4's content scanner to
  read Jinja templates (the v4 auto-detector ignores ``.html.j2`` by default).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.lib.settings import BASE_DIR

if TYPE_CHECKING:
    from pathlib import Path

STYLES_PATH: Path = BASE_DIR.parents[1] / "src" / "resources" / "styles.css"


def test_styles_imports_tailwind() -> None:
    body = STYLES_PATH.read_text(encoding="utf-8")
    assert '@import "tailwindcss"' in body, (
        'src/resources/styles.css must @import "tailwindcss" to enable Tailwind v4 CSS-first config'
    )


def test_styles_sources_web_templates() -> None:
    body = STYLES_PATH.read_text(encoding="utf-8")
    assert '@source "../app/domain/web/templates"' in body, (
        "src/resources/styles.css must @source the web-domain Jinja templates so Tailwind v4 scans them"
    )

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Phase 4.4 contract: ``CSRF_HEADER_NAME`` is renamed from ``X-XSRF-TOKEN``
to ``X-CSRFToken`` so ``registerHtmxExtension()`` (which forwards
``X-CSRFToken`` by default) works without a client-side patch.
"""

from __future__ import annotations

from app.lib.settings import AppSettings


def test_csrf_header_default_is_x_csrf_token() -> None:
    """Default header name must match litestar-vite-plugin's helper default."""
    assert AppSettings().CSRF_HEADER_NAME == "X-CSRFToken", (
        f"CSRF_HEADER_NAME default must be X-CSRFToken; got {AppSettings().CSRF_HEADER_NAME!r}"
    )

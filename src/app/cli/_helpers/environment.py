# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Environment setup for the ``coffee`` CLI."""

from __future__ import annotations

import os


def setup_environment() -> None:
    """Configure environment variables shared by every ``coffee`` invocation."""
    from app import config
    from app.lib.log import set_cli_mode
    from app.lib.settings import get_settings

    _ = config.log.structlog_logging_config.configure()()
    config.setup_logging()
    set_cli_mode(True)
    settings = get_settings()
    os.environ.setdefault("LITESTAR_APP", "app.server.asgi:create_app")
    os.environ.setdefault("LITESTAR_APP_NAME", settings.app.NAME)
    os.environ.setdefault("LITESTAR_GRANIAN_IN_SUBPROCESS", "false")
    os.environ.setdefault("LITESTAR_GRANIAN_USE_LITESTAR_LOGGER", "true")

# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Environment setup for the ``coffee`` CLI."""

from __future__ import annotations


def setup_environment() -> None:
    """Configure environment variables shared by every ``coffee`` invocation."""
    from app import config
    from app.lib.log import set_cli_mode
    from app.lib.settings import get_settings

    config.setup_logging()
    set_cli_mode(True)
    settings = get_settings()
    settings.setup_litestar_env()

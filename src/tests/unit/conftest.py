# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit test configuration and shared unit-tier hooks."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from app import config as app_config
from app.lib.settings import Settings

if TYPE_CHECKING:
    import pytest

os.environ.setdefault("QUEUE_BACKEND", "memory")


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Ensure unit tests default to the in-memory queue backend without live Oracle connections."""
    del item
    os.environ["QUEUE_BACKEND"] = "memory"
    Settings.from_env.cache_clear()
    app_config._reset()


def pytest_runtest_teardown(item: pytest.Item) -> None:
    """Reset cached settings and plugin state after each unit test."""
    del item
    os.environ["QUEUE_BACKEND"] = "memory"
    Settings.from_env.cache_clear()
    app_config._reset()

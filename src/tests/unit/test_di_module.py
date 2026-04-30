# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Architectural tests for ``app.lib.di``."""

from __future__ import annotations

import inspect

import pytest

import app.lib.di as di_module

DEAD_NAMES = (
    "request_container_var",
    "worker_container_var",
    "job_inject",
    "worker_scope",
    "with_websocket_request",
    "get_from_connection",
    "WebSocketScope",
    "provide_websocket_scope",
)


@pytest.mark.parametrize("name", DEAD_NAMES)
def test_dead_name_is_removed(name: str) -> None:
    assert not hasattr(di_module, name)


@pytest.mark.parametrize("name", DEAD_NAMES)
def test_dead_name_not_in_all(name: str) -> None:
    assert name not in di_module.__all__


def test_async_inject_does_not_reference_dead_names() -> None:
    from app.cli import utils as cli_utils

    source = inspect.getsource(cli_utils)
    for name in DEAD_NAMES:
        assert name not in source, f"{name} still referenced in cli/utils.py"


def test_di_module_exports_live_surface() -> None:
    expected = {
        "Inject",
        "LitestarProvider",
        "LitestarRouter",
        "QueryContext",
        "Scope",
        "query_id_var",
        "setup_dishka",
    }
    assert set(di_module.__all__) == expected

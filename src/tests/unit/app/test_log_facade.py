# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the public logging facade."""

from __future__ import annotations

from app.lib.log import (
    BeforeSendHandler,
    EventFilter,
    StructlogMiddleware,
    SuppressADKWarningsFilter,
    SuppressAsyncioTaskExceptionFilter,
    SuppressGranianExcInfoFilter,
    after_exception_hook_handler,
    build_security_headers,
    stdlib_json_serializer,
    structlog_json_serializer,
)
from tests.support.paths import APP_ROOT


def test_log_public_surface_reexports_focused_private_implementations() -> None:
    """The public log module should read as an API facade over focused helpers."""
    assert SuppressADKWarningsFilter.__module__ == "app.lib.log._filters"
    assert SuppressAsyncioTaskExceptionFilter.__module__ == "app.lib.log._filters"
    assert SuppressGranianExcInfoFilter.__module__ == "app.lib.log._filters"
    assert build_security_headers.__module__ == "app.lib.log._security"
    assert EventFilter.__module__ == "app.lib.log._processors"
    assert structlog_json_serializer.__module__ == "app.lib.log._processors"
    assert stdlib_json_serializer.__module__ == "app.lib.log._processors"
    assert StructlogMiddleware.__module__ == "app.lib.log._middleware"
    assert BeforeSendHandler.__module__ == "app.lib.log._middleware"
    assert after_exception_hook_handler.__module__ == "app.lib.log._middleware"


def test_log_private_implementations_live_under_log_package() -> None:
    """Logging helper modules should stay grouped under the public log package."""
    lib_root = APP_ROOT / "lib"
    log_package = lib_root / "log"

    assert log_package.is_dir()
    assert (log_package / "__init__.py").is_file()
    assert {path.name for path in log_package.glob("_*.py") if path.name != "__init__.py"} == {
        "_filters.py",
        "_middleware.py",
        "_processors.py",
        "_security.py",
    }
    assert not any(lib_root.glob("_log_*.py"))

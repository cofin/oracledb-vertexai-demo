# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for logging configuration and log filters."""

from __future__ import annotations

import logging
import os
import re

import pytest

from app import config
from app.lib import log as log_conf
from app.lib.log import (
    EventFilter,
    SuppressAsyncioTaskExceptionFilter,
    SuppressGranianExcInfoFilter,
    is_cli_mode,
    set_cli_mode,
)
from app.lib.settings import LogSettings, Settings


def _log_record(name: str, msg: str, exc_info: object = None) -> logging.LogRecord:
    """Create a synthetic `logging.LogRecord` for filter testing."""
    return logging.LogRecord(
        name=name,
        level=logging.ERROR if name == "_granian" else logging.WARNING,
        pathname="foo.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=exc_info,  # type: ignore[arg-type]
    )


def test_cli_mode() -> None:
    """Test setting and getting CLI mode."""
    set_cli_mode(False)
    assert not is_cli_mode()
    set_cli_mode(True)
    assert is_cli_mode()
    set_cli_mode(False)
    assert not is_cli_mode()


def test_suppress_asyncio_task_exception_filter_hides_duplicate_task_warning() -> None:
    """Duplicate asyncio task-exception warnings are suppressed while runtime errors pass."""
    log_filter = SuppressAsyncioTaskExceptionFilter()
    assert not log_filter.filter(_log_record("asyncio", "Task exception was never retrieved"))
    assert log_filter.filter(_log_record("asyncio", "Application callable raised an exception"))


def test_config_register_reset_hook_invoked_on_reset() -> None:
    """Registered reset hooks fire whenever config._reset() clears cached configuration."""
    calls: list[str] = []

    def _on_reset() -> None:
        calls.append("reset")

    config.register_reset_hook(_on_reset)
    try:
        config._reset()
        assert calls == ["reset"]
    finally:
        config._reset_hooks.remove(_on_reset)


def test_setup_logging_does_not_force_config_initialization() -> None:
    """Verify config.setup_logging() configures logging without materializing database pools via _initialize()."""
    config._reset()
    try:
        assert config._initialized is False
        config.setup_logging()
        assert config._initialized is False
    finally:
        config._reset()


def test_log_settings_excludes_static_assets_by_default() -> None:
    """Static asset requests should not drown out chat/API logs."""
    exclude_paths = re.compile(LogSettings().EXCLUDE_PATHS)

    assert exclude_paths.search("/static/dist/cymbal-coffee-logo.svg")
    assert exclude_paths.search("/favicon.ico")
    assert exclude_paths.search("/assets/app.css")
    assert not exclude_paths.search("/api/chat/stream")


def test_settings_sets_litestar_granian_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings should carry the default server logging environment variables without deprecated Granian flags."""
    for key in (
        "LITESTAR_APP",
        "LITESTAR_APP_NAME",
        "LITESTAR_GRANIAN_IN_SUBPROCESS",
        "LITESTAR_GRANIAN_USE_LITESTAR_LOGGER",
    ):
        monkeypatch.delenv(key, raising=False)

    Settings.from_env.cache_clear()
    try:
        settings = Settings.from_env(dotenv_filename=".missing-env")

        assert os.environ["LITESTAR_APP"] == "app.server.asgi:create_app"
        assert os.environ["LITESTAR_APP_NAME"] == settings.app.NAME
        assert "LITESTAR_GRANIAN_IN_SUBPROCESS" not in os.environ
        assert "LITESTAR_GRANIAN_USE_LITESTAR_LOGGER" not in os.environ
    finally:
        Settings.from_env.cache_clear()


def test_structlog_config_uses_tty_processors(monkeypatch: pytest.MonkeyPatch) -> None:
    """TTY stdlib logs should filter duplicate message fields."""
    monkeypatch.setattr(log_conf, "is_tty", lambda: True)
    config._reset()
    try:
        log_config = config.log
        standard_lib_config = log_config.structlog_logging_config.standard_lib_logging_config
        assert standard_lib_config is not None

        formatter = standard_lib_config.formatters["standard"]
        processors = formatter["processors"]

        names = {getattr(processor, "__name__", processor.__class__.__name__) for processor in processors}
        assert "add_logger_name_safe" in names
        assert "add_logger_source" in names
        assert any(
            isinstance(processor, EventFilter) and "message" in processor.filter_keys for processor in processors
        )
    finally:
        config._reset()


@pytest.mark.parametrize(
    ("msg", "exc_info", "expected", "expect_exc_cleared"),
    [
        ('Traceback (most recent call last):\n  ... \nrelation "job" does not exist', None, False, False),
        ("Traceback (most recent call last):\n  ... \nSystemExit: 1", None, False, False),
        (
            "Traceback (most recent call last):\n  ... \nSome other error",
            (Exception, Exception("test"), None),
            True,
            True,
        ),
    ],
)
def test_suppress_granian_exc_info_filter(msg: str, exc_info: object, expected: bool, expect_exc_cleared: bool) -> None:
    """Handled errors and SystemExit are suppressed; unhandled errors pass but lose exc_info."""
    record = _log_record("_granian", msg, exc_info=exc_info)
    assert SuppressGranianExcInfoFilter().filter(record) is expected
    if expect_exc_cleared:
        assert record.exc_info is None

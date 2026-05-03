# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for logging configuration."""

import logging
import os
import re

from app.lib.log import (
    EventFilter,
    SuppressADKWarningsFilter,
    SuppressGranianExcInfoFilter,
    is_cli_mode,
    set_cli_mode,
)
from app.lib.settings import LogSettings, Settings


def test_cli_mode():
    """Test setting and getting CLI mode."""
    set_cli_mode(False)
    assert not is_cli_mode()
    set_cli_mode(True)
    assert is_cli_mode()
    set_cli_mode(False)
    assert not is_cli_mode()


def test_suppress_adk_warnings_filter_hides_known_third_party_noise():
    """Known ADK/Authlib warning noise should not hide real runtime errors."""
    filter_ = SuppressADKWarningsFilter()
    messages = [
        "[EXPERIMENTAL] feature FeatureName.PLUGGABLE_AUTH is enabled.",
        "[EXPERIMENTAL] feature FeatureName.PROGRESSIVE_SSE_STREAMING is enabled.",
        "AuthlibDeprecationWarning: authlib.jose module is deprecated, please use joserfc instead.",
        "Warning: returning concatenated text result from text parts.",
    ]

    for message in messages:
        record = logging.LogRecord(
            name="py.warnings",
            level=logging.WARNING,
            pathname="foo.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        assert filter_.filter(record) is False


def test_suppress_adk_warnings_filter_keeps_unexpected_warnings():
    """The warning filter must stay narrow so real signals remain visible."""
    filter_ = SuppressADKWarningsFilter()
    record = logging.LogRecord(
        name="py.warnings",
        level=logging.WARNING,
        pathname="foo.py",
        lineno=1,
        msg="Application callable raised an exception",
        args=(),
        exc_info=None,
    )
    assert filter_.filter(record) is True


def test_log_settings_excludes_static_assets_by_default():
    """Static asset requests should not drown out chat/API logs."""
    exclude_paths = re.compile(LogSettings().EXCLUDE_PATHS)

    assert exclude_paths.search("/static/dist/cymbal-coffee-logo.svg")
    assert exclude_paths.search("/favicon.ico")
    assert exclude_paths.search("/assets/app.css")
    assert not exclude_paths.search("/api/chat/stream")


def test_settings_sets_litestar_granian_env(monkeypatch):
    """Settings should carry accelerator's server logging environment defaults."""
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
        assert os.environ["LITESTAR_GRANIAN_IN_SUBPROCESS"] == "false"
        assert os.environ["LITESTAR_GRANIAN_USE_LITESTAR_LOGGER"] == "true"
    finally:
        Settings.from_env.cache_clear()


def test_structlog_config_uses_accelerator_style_tty_processors(monkeypatch):
    """TTY stdlib logs should filter duplicate message fields like accelerator."""
    from app import config
    from app.lib import log as log_conf

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


def test_suppress_granian_exc_info_filter_handled_error():
    """Test that handled errors are suppressed."""
    filter_ = SuppressGranianExcInfoFilter()
    record = logging.LogRecord(
        name="_granian",
        level=logging.ERROR,
        pathname="foo.py",
        lineno=1,
        msg='Traceback (most recent call last):\n  ... \nrelation "job" does not exist',
        args=(),
        exc_info=None,
    )
    assert filter_.filter(record) is False


def test_suppress_granian_exc_info_filter_system_exit():
    """Test that SystemExit: 1 is suppressed."""
    filter_ = SuppressGranianExcInfoFilter()
    record = logging.LogRecord(
        name="_granian",
        level=logging.ERROR,
        pathname="foo.py",
        lineno=1,
        msg="Traceback (most recent call last):\n  ... \nSystemExit: 1",
        args=(),
        exc_info=None,
    )
    assert filter_.filter(record) is False


def test_suppress_granian_exc_info_filter_unhandled_error():
    """Test that unhandled errors are not suppressed but exc_info is cleared."""
    filter_ = SuppressGranianExcInfoFilter()
    record = logging.LogRecord(
        name="_granian",
        level=logging.ERROR,
        pathname="foo.py",
        lineno=1,
        msg="Traceback (most recent call last):\n  ... \nSome other error",
        args=(),
        exc_info=(Exception, Exception("test"), None),
    )
    assert filter_.filter(record) is True
    assert record.exc_info is None

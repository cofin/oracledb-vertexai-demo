# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for logging configuration."""

import logging

from app.lib.log import SuppressGranianExcInfoFilter, is_cli_mode, set_cli_mode


def test_cli_mode():
    """Test setting and getting CLI mode."""
    set_cli_mode(False)
    assert not is_cli_mode()
    set_cli_mode(True)
    assert is_cli_mode()
    set_cli_mode(False)
    assert not is_cli_mode()


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

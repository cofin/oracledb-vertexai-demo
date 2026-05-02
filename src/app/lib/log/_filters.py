# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Logging filters for known noisy third-party/runtime messages."""

from __future__ import annotations

import logging


class SuppressADKWarningsFilter(logging.Filter):
    """Filter to suppress specific ADK/GenAI warnings that clutter demo logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress log record."""
        msg = record.getMessage()
        suppressed_fragments = (
            "FeatureName.PLUGGABLE_AUTH is enabled",
            "FeatureName.PROGRESSIVE_SSE_STREAMING is enabled",
            "authlib.jose module is deprecated",
            "returning concatenated text result from text parts",
        )
        if any(fragment in msg for fragment in suppressed_fragments):
            return False
        return not ("non-text parts in the response" in msg and "function_call" in msg)


class SuppressAsyncioTaskExceptionFilter(logging.Filter):
    """Filter to suppress asyncio task warnings that duplicate handled errors."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "Task exception was never retrieved" not in msg


class SuppressGranianExcInfoFilter(logging.Filter):
    """Filter duplicate traceback logging from Granian lifespan/error paths."""

    _HANDLED_ERRORS = ('relation "job" does not exist', "SystemExit: 1")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()

        if "Traceback (most recent call last)" in msg:
            if any(err in msg for err in self._HANDLED_ERRORS):
                return False

            record.exc_info = None
            record.exc_text = None
            return True

        if record.exc_info and "lifespan" in msg.lower():
            record.exc_info = None
            record.exc_text = None

        return True

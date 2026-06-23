# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Structlog processor and serializer helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.utils.serialization import to_json

if TYPE_CHECKING:
    from collections.abc import Iterable

    from structlog.types import EventDict, WrappedLogger
    from structlog.typing import Processor


def structlog_json_serializer(value: EventDict, **_: Any) -> bytes:
    return to_json(value, as_bytes=True)


def stdlib_json_serializer(value: EventDict, **_: Any) -> str:
    return to_json(value, as_bytes=False)


def add_logger_name_safe(logger: WrappedLogger, _: str, event_dict: EventDict) -> EventDict:
    """Safely add logger name, handling both stdlib and native structlog loggers."""
    record = event_dict.get("_record")
    if record is not None:
        event_dict["logger"] = record.name
    elif hasattr(logger, "name"):
        event_dict["logger"] = logger.name
    elif hasattr(logger, "_name"):
        event_dict["logger"] = logger._name  # noqa: SLF001
    return event_dict


def add_logger_source(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Move the full logger name into a source field for readable demo logs."""
    if logger_name := event_dict.get("logger"):
        event_dict["source"] = logger_name
        event_dict.pop("logger", None)
    return event_dict


def add_google_cloud_attributes(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Add Google Cloud-compatible log fields."""
    event_dict["severity"] = event_dict.get("level")
    event_dict["labels"] = None
    event_dict["resource"] = None
    if event_dict.get("logger"):
        event_dict["python_logger"] = event_dict.pop("logger")
    return event_dict


class EventFilter:
    """Remove keys from the log event."""

    def __init__(self, filter_keys: Iterable[str]) -> None:
        """Event filter."""
        self.filter_keys = filter_keys

    def __call__(self, _: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
        """Receive the log event, and filter keys."""
        for key in self.filter_keys:
            event_dict.pop(key, None)
        return event_dict


def structlog_processors(as_json: bool) -> list[Processor]:
    """Set the default processors for structlog."""
    try:
        import structlog
        from structlog.dev import RichTracebackFormatter

        if as_json:
            return [
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                add_logger_name_safe,
                add_logger_source,
                structlog.processors.format_exc_info,
                add_google_cloud_attributes,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(serializer=structlog_json_serializer),
            ]
        return [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            add_logger_name_safe,
            add_logger_source,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(
                colors=True, exception_formatter=RichTracebackFormatter(max_frames=1, show_locals=False, width=80)
            ),
        ]
    except ImportError:
        return []


def stdlib_logger_processors(as_json: bool) -> list[Processor]:
    """Set the default processors for structlog stdlib."""
    try:
        import structlog
        from structlog.dev import RichTracebackFormatter

        if as_json:
            return [
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                add_logger_name_safe,
                add_logger_source,
                structlog.stdlib.ExtraAdder(),
                EventFilter(["color_message"]),
                structlog.processors.EventRenamer("message"),
                add_google_cloud_attributes,
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(serializer=stdlib_json_serializer),
            ]
        return [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            add_logger_name_safe,
            add_logger_source,
            structlog.stdlib.ExtraAdder(),
            EventFilter(["color_message"]),
            EventFilter(["message"]),
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(
                colors=True, exception_formatter=RichTracebackFormatter(max_frames=1, show_locals=False, width=80)
            ),
        ]
    except ImportError:
        return []

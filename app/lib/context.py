"""Thread-safe context management for request-scoped data.

This module provides context variables for storing request-specific data
like timing information in a thread-safe manner, replacing global dictionaries.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# Thread-safe context variable for timing data
_timing_context: ContextVar[dict[str, Any] | None] = ContextVar("timing_context", default=None)


def get_timing_context() -> dict[str, Any]:
    """Get current request's timing context.

    Returns:
        Dictionary containing timing data for the current request
    """
    ctx = _timing_context.get()
    if ctx is None:
        return {}
    return ctx.copy()


def set_timing_data(key: str, data: dict[str, Any]) -> None:
    """Set timing data for current request.

    Args:
        key: Timing data key (e.g., 'vector_search', 'intent_classification')
        data: Timing data dictionary
    """
    ctx = _timing_context.get()
    if ctx is None:
        ctx = {}
    ctx[key] = data
    _timing_context.set(ctx)


def clear_timing_context() -> dict[str, Any]:
    """Clear and return timing context.

    Returns:
        The timing context before clearing
    """
    ctx = _timing_context.get()
    if ctx is None:
        return {}
    _timing_context.set(None)
    return ctx


def reset_timing_context() -> None:
    """Reset timing context to empty state.

    Useful for test setup and initialization.
    """
    _timing_context.set(None)

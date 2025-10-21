"""Request context variables for propagating request-scoped data."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass

query_id_var: ContextVar[str | None] = ContextVar("query_id", default=None)


@dataclass
class QueryContext:
    """Request-scoped query context."""

    query_id: str

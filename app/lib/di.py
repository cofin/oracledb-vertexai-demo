"""Dependency injection utilities and request context.

This module provides a clean interface to the underlying DI framework
(Dishka) without exposing implementation details throughout the codebase,
plus request-scoped context variables for propagating data.

The clean naming pattern (`Inject` instead of `FromDishka`) improves
code readability and makes it easier to swap DI frameworks in the future.

Example:
    from app.lib.di import Inject, inject

    class MyController(Controller):
        @get("/")
        @inject
        async def handler(self, service: Inject[MyService]) -> Response:
            ...
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass

from dishka import AsyncContainer, Provider, Scope, provide
from dishka.integrations.litestar import (
    FromDishka as Inject,
)
from dishka.integrations.litestar import LitestarProvider, inject, setup_dishka

# Request context variables
query_id_var: ContextVar[str | None] = ContextVar("query_id", default=None)


@dataclass
class QueryContext:
    """Request-scoped query context."""

    query_id: str


__all__ = (
    "AsyncContainer",
    "Inject",
    "LitestarProvider",
    "Provider",
    "QueryContext",
    "Scope",
    "inject",
    "provide",
    "query_id_var",
    "setup_dishka",
)

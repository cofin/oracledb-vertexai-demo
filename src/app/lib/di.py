# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dependency injection re-exports and request-scoped query context."""

from contextvars import ContextVar
from dataclasses import dataclass

from dishka import Scope
from dishka.integrations.litestar import DishkaRouter as LitestarRouter
from dishka.integrations.litestar import FromDishka as Inject
from dishka.integrations.litestar import LitestarProvider, setup_dishka

query_id_var: ContextVar[str | None] = ContextVar("query_id", default=None)


@dataclass
class QueryContext:
    """Request-scoped query identifier."""

    query_id: str


__all__ = (
    "Inject",
    "LitestarProvider",
    "LitestarRouter",
    "QueryContext",
    "Scope",
    "query_id_var",
    "setup_dishka",
)

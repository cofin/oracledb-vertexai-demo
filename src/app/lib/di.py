# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dependency injection re-exports and active container context variables."""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

from dishka.integrations.litestar import DishkaRouter as LitestarRouter
from dishka.integrations.litestar import FromDishka as Inject
from dishka.integrations.litestar import LitestarProvider, setup_dishka

if TYPE_CHECKING:
    from dishka import AsyncContainer

__all__ = (
    "Inject",
    "LitestarProvider",
    "LitestarRouter",
    "request_container_var",
    "setup_dishka",
    "worker_container_var",
)

request_container_var: ContextVar[AsyncContainer | None] = ContextVar(
    "request_container",
    default=None,
)
worker_container_var: ContextVar[AsyncContainer | None] = ContextVar(
    "worker_container",
    default=None,
)

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka container resolution helpers for ``litestar-queues`` background tasks."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from dishka import AsyncContainer, Scope

from app.ioc import create_container
from app.lib.di import request_container_var, worker_container_var

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = ("get_task_container", "request_container_var", "task_container_scope", "worker_container_var")


def get_task_container() -> AsyncContainer:
    """Return the active request-scoped Dishka container inside a task execution scope.

    Raises:
        RuntimeError: If no active request or worker container scope has been entered.
    """
    active = request_container_var.get()
    if active is not None:
        return active
    msg = "No active Dishka task container in context; wrap task execution in task_container_scope()."
    raise RuntimeError(msg)


@asynccontextmanager
async def task_container_scope() -> AsyncGenerator[AsyncContainer, None]:
    """Yield a request-scoped Dishka ``AsyncContainer`` for a background task execution.

    Reuses ``request_container_var`` when already active (e.g. inline tests or
    HTTP request context), opens a ``Scope.REQUEST`` child from
    ``worker_container_var`` when running inside a shared worker container, or
    creates and closes a managed root ``create_container()`` instance otherwise.

    Yields:
        A request-scoped ``AsyncContainer`` instance.
    """
    active_request = request_container_var.get()
    if active_request is not None:
        yield active_request
        return

    worker_root = worker_container_var.get()
    if worker_root is not None:
        async with worker_root(scope=Scope.REQUEST) as scoped_container:
            token = request_container_var.set(scoped_container)
            try:
                yield scoped_container
            finally:
                request_container_var.reset(token)
        return

    root_container = create_container()
    try:
        async with root_container(scope=Scope.REQUEST) as scoped_container:
            token = request_container_var.set(scoped_container)
            try:
                yield scoped_container
            finally:
                request_container_var.reset(token)
    finally:
        await root_container.close()

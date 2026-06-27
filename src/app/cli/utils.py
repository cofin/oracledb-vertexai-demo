# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Async dependency injection for click commands."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, cast, get_type_hints

import rich_click as click
from dishka import Scope
from sqlspec.utils.sync_tools import run_

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from dishka import AsyncContainer


def async_inject[**P, R](func: Callable[P, Awaitable[R]]) -> Callable[P, R]:
    """Wrap an async click command so its annotated dependencies are injected.

    Resolves the container factory from ``ctx.obj["container_factory"]`` when
    available so server commands can swap in a Litestar-flavored container;
    falls back to the plain CLI factory otherwise.

    Returns:
        A sync wrapper that runs ``func`` inside a Dishka REQUEST scope.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        async def _runner() -> R:
            from app.ioc import make_container

            ctx = click.get_current_context(silent=True)
            container_factory = None
            if ctx is not None and isinstance(ctx.obj, dict):
                container_factory = ctx.obj.get("container_factory")
            if container_factory is None:
                container_factory = make_container

            container = cast("AsyncContainer", container_factory())
            try:
                async with container(scope=Scope.REQUEST) as request_container:
                    injected = await _resolve_dependencies(func, request_container, kwargs)
                    return await func(*args, **{**kwargs, **injected})
            finally:
                await container.close()

        return run_(_runner)()

    return cast("Callable[P, R]", wrapper)


async def _resolve_dependencies(
    func: Callable[..., Any], container: AsyncContainer, existing_kwargs: dict[str, Any]
) -> dict[str, Any]:
    injected: dict[str, Any] = {}
    for name, type_hint in get_type_hints(func).items():
        if name == "return" or name in existing_kwargs:
            continue
        try:
            injected[name] = await container.get(type_hint)
        except Exception:  # noqa: BLE001, S112
            continue
    return injected

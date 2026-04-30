# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Async dependency injection for click commands."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast, get_type_hints

from dishka import Scope
from sqlspec.utils.sync_tools import run_

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from dishka import AsyncContainer

P = ParamSpec("P")
R = TypeVar("R")


def async_inject(func: Callable[P, Awaitable[R]]) -> Callable[P, R]:
    """Wrap an async click command so its annotated dependencies are injected.

    Returns:
        A sync wrapper that runs ``func`` inside a Dishka REQUEST scope.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        async def _runner() -> R:
            from app.ioc import make_litestar_container

            container = make_litestar_container()
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

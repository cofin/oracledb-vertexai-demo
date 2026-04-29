"""CLI utilities — async injection adapted from dma/cli/utils.py."""

from __future__ import annotations

from collections.abc import Awaitable, Callable  # noqa: TC003 — needed at runtime by @wraps
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast, get_type_hints

from sqlspec.utils.sync_tools import run_

from app.lib.di import Scope, request_container_var, worker_container_var

if TYPE_CHECKING:
    from dishka import AsyncContainer

P = ParamSpec("P")
R = TypeVar("R")


def async_inject(func: Callable[P, Awaitable[R]]) -> Callable[P, R]:
    """Run an async click command with Dishka injection.

    Inspects the wrapped function's type hints, builds a fresh CLI-scoped
    Dishka container (REQUEST scope), and resolves any annotated dependencies
    from it. Sets ``worker_container_var`` and ``request_container_var`` so the
    code under the command can use ``worker_scope()`` and ``@job_inject``
    against the same scope.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        async def _runner() -> R:
            from app.ioc import make_litestar_container

            container = make_litestar_container()
            try:
                worker_token = worker_container_var.set(container)
                try:
                    async with container(scope=Scope.REQUEST) as request_container:
                        request_token = request_container_var.set(request_container)
                        try:
                            injected = await _resolve_dependencies(func, request_container, kwargs)
                            return await func(*args, **{**kwargs, **injected})
                        finally:
                            request_container_var.reset(request_token)
                finally:
                    worker_container_var.reset(worker_token)
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
        except Exception:  # noqa: BLE001, S112 — params with no provider are click-only kwargs
            continue
    return injected

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
        @inject(signature_types=(MyService,))
        async def handler(self, service: Inject[MyService]) -> Response:
            ...
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from dishka import AsyncContainer, Provider, Scope, provide
from dishka.integrations.litestar import (
    FromDishka as Inject,
)
from dishka.integrations.litestar import (
    LitestarProvider,
)
from dishka.integrations.litestar import (
    inject as _dishka_inject,
)
from dishka.integrations.litestar import (
    setup_dishka as _dishka_setup,
)
from litestar import Litestar, Router
from litestar.routes import ASGIRoute, HTTPRoute, WebSocketRoute

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

_PENDING_ATTR = "__app_pending_dishka_injection__"

_T = TypeVar("_T")


class _PendingInjection:
    __slots__ = ("namespace", "types")

    def __init__(
        self,
        namespace: Mapping[str, Any] | None,
        signature_types: Sequence[type[Any]] | None,
    ) -> None:
        self.namespace = dict(namespace or {})
        self.types = tuple(signature_types or ())


def inject(
    func: Callable[..., _T] | None = None,
    *,
    signature_namespace: Mapping[str, Any] | None = None,
    signature_types: Sequence[type[Any]] | None = None,
) -> Callable[..., _T] | Callable[[Callable[..., _T]], Callable[..., _T]]:
    """Mark a handler for Dishka injection after Litestar attaches namespaces."""

    def decorator(target: Callable[..., _T]) -> Callable[..., _T]:
        setattr(
            target,
            _PENDING_ATTR,
            _PendingInjection(signature_namespace, signature_types),
        )
        return target

    if func is not None:
        return decorator(func)
    return decorator


def setup_dishka(container: AsyncContainer, app: Litestar) -> None:
    _apply_pending_injections(app)
    _dishka_setup(container, app)


def _apply_pending_injections(app: Litestar) -> None:
    for route in app.routes:
        _apply_pending_injections_to_route(route)


def _apply_pending_injections_to_route(route: Any) -> None:
    if isinstance(route, HTTPRoute):
        for handler in route.route_handlers:
            _inject_handler(handler)
    elif isinstance(route, (WebSocketRoute, ASGIRoute)):
        _inject_handler(route.route_handler)
    if isinstance(route, Router):
        for child in route.routes:
            _apply_pending_injections_to_route(child)


def _inject_handler(handler: Any) -> None:
    try:
        fn = handler.fn
    except Exception:  # pragma: no cover - defensive  # noqa: BLE001
        return

    pending: _PendingInjection | None = getattr(fn, _PENDING_ATTR, None)
    if pending is None:
        return

    namespace = handler.resolve_signature_namespace().copy()
    namespace.update(pending.namespace)
    namespace.update({type_.__name__: type_ for type_ in pending.types})

    _ensure_forward_refs(fn, namespace)
    injected = _dishka_inject(fn)
    handler._fn = injected  # noqa: SLF001
    delattr(fn, _PENDING_ATTR)


def _ensure_forward_refs(target: Callable[..., Any], namespace: Mapping[str, Any]) -> None:
    func_globals = getattr(target, "__globals__", None)
    if func_globals is None:
        return
    for name, value in namespace.items():
        func_globals.setdefault(name, value)


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

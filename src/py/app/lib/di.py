"""Dependency injection utilities and request context.

This module provides a clean interface to the underlying DI framework
(Dishka) without exposing implementation details throughout the codebase.

The clean naming pattern (`Inject` instead of `FromDishka`) improves
code readability and makes it easier to swap DI frameworks in the future.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from inspect import iscoroutinefunction, signature
from typing import TYPE_CHECKING, Annotated, Any, TypeVar, get_args, get_origin

import structlog
from dishka import (
    AsyncContainer,
    Container,
    FromComponent,
    Provider,
    Scope,
    make_async_container,
    make_container,
    provide,
)
from dishka.integrations.litestar import DishkaRouter as LitestarRouter
from dishka.integrations.litestar import FromDishka as Inject
from dishka.integrations.litestar import LitestarProvider, setup_dishka

if TYPE_CHECKING:
    from litestar import WebSocket
    from litestar.connection import ASGIConnection

logger = structlog.get_logger()

# FromComponent is a function that returns an instance of _FromComponent.
# We need the type for isinstance checks.
_FromComponentType = type(FromComponent())


query_id_var: ContextVar[str | None] = ContextVar("query_id", default=None)
request_container_var: ContextVar[AsyncContainer | None] = ContextVar("request_container", default=None)
worker_container_var: ContextVar[AsyncContainer | None] = ContextVar("worker_container", default=None)

T = TypeVar("T")


@dataclass
class QueryContext:
    """Request-scoped query context."""

    query_id: str


@asynccontextmanager
async def worker_scope() -> AsyncIterator[AsyncContainer]:
    """Enter a temporary REQUEST scope using the worker container.

    Use this in background jobs to create short-lived database sessions
    instead of holding a session open for the entire job duration.
    """
    container = worker_container_var.get()
    if not container:
        msg = "No worker container found in context. Are you running in a worker?"
        raise RuntimeError(msg)

    async with container(scope=Scope.REQUEST) as request_container:
        yield request_container


def job_inject(func: Callable) -> Callable:
    """Decorator to inject dependencies into background jobs.

    Uses request_container_var to resolve dependencies from the active
    REQUEST scope managed by the Worker.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        container = request_container_var.get()
        if not container:
            # Fallback to no injection if no container found in context
            return await func(*args, **kwargs) if iscoroutinefunction(func) else func(*args, **kwargs)

        # Resolve dependencies from container
        sig = signature(func)
        injected_kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name in kwargs:
                continue

            is_dependency = False

            # Unwrap Annotated (Inject[T] is Annotated[T, FromDishka()])
            dependency_type = param.annotation
            if get_origin(param.annotation) is Annotated:
                args_origin = get_args(param.annotation)
                # Check for Inject (legacy) or FromComponent (new Inject[T])
                if args_origin and any(isinstance(a, (Inject, _FromComponentType)) for a in args_origin[1:]):  # type: ignore[arg-type]
                    dependency_type = args_origin[0]
                    is_dependency = True

            if is_dependency:
                try:
                    # Resolve from Dishka
                    dep = await container.get(dependency_type)
                    injected_kwargs[param_name] = dep
                except Exception:  # noqa: BLE001
                    # Skip if cannot resolve (might be a normal argument)
                    logger.debug("Failed to inject dependency", param=param_name, error=True)
                    continue

        final_kwargs = {**kwargs, **injected_kwargs}
        if iscoroutinefunction(func):
            return await func(*args, **final_kwargs)
        return func(*args, **final_kwargs)

    return wrapper


@asynccontextmanager
async def get_from_connection(
    connection: "ASGIConnection[Any, Any, Any, Any]", dependency_type: type[T]
) -> AsyncIterator[T]:
    """Get a dependency from the Dishka container via the connection.

    This is useful for code that runs outside of route handlers but still
    has access to the connection (e.g., JWT auth callbacks, middleware).

    For WebSocket connections (SESSION scope), this automatically creates a
    temporary REQUEST scope to resolve REQUEST-scoped dependencies like
    database services. The scope is properly cleaned up when the context exits.

    Args:
        connection: The ASGI connection (Request or WebSocket).
        dependency_type: The type of dependency to retrieve (can be abstract).

    Yields:
        The resolved dependency instance.

    Example:
        ```python
        async with get_from_connection(connection, UserService) as service:
            user = await service.get_user(user_id)
        ```
    """
    container: AsyncContainer = connection.state.dishka_container
    yield await container.get(dependency_type)


@asynccontextmanager
async def with_websocket_request(connection: "ASGIConnection[Any, Any, Any, Any]") -> AsyncIterator[AsyncContainer]:
    """Enter a temporary REQUEST scope for brief database operations.

    Use this in WebSocket handlers to get REQUEST-scoped services (like those
    requiring database connections) without holding the connection open for
    the entire WebSocket session.

    Dishka creates SESSION-scoped containers for WebSocket connections (long-lived),
    but services requiring DB connections are registered with REQUEST scope (short-lived).
    REQUEST is a child of SESSION in Dishka's hierarchy, so we must explicitly create
    a child container to resolve these services.

    Args:
        connection: The ASGI connection (typically a WebSocket).

    Yields:
        A REQUEST-scoped container for resolving services.

    Example:
        ```python
        @websocket(path="/stream")
        async def my_websocket(self, socket: WebSocket) -> None:
            async with with_websocket_request(socket) as container:
                service = await container.get(MyService)
                result = await service.check_something()
            # DB connection released here
            await socket.accept()
            # ... long-lived work
        ```
    """
    session_container: AsyncContainer = connection.state.dishka_container
    async with session_container({}, scope=Scope.REQUEST) as request_container:
        yield request_container


class WebSocketScope:
    """Factory for creating short-lived REQUEST scopes in WebSocket handlers.

    Use this as a Litestar dependency to get a callable that creates
    temporary REQUEST scopes for database operations.

    Example:
        ```python
        from litestar import WebSocket, websocket

        def provide_websocket_scope(socket: WebSocket) -> WebSocketScope:
            return WebSocketScope(socket)

        class MyController(Controller):
            dependencies = {"db_scope": Provide(provide_websocket_scope)}

            @websocket(path="/stream")
            async def stream(self, socket: WebSocket, db_scope: WebSocketScope) -> None:
                await socket.accept()
                # Later, when you need DB access:
                async with db_scope() as container:
                    service = await container.get(MyService)
                    result = await service.do_something()
                # DB connection released, continue streaming...
        ```
    """

    def __init__(self, connection: "ASGIConnection[Any, Any, Any, Any]") -> None:
        """Initialize with the WebSocket connection.

        Args:
            connection: The WebSocket connection.
        """
        self._connection = connection

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[AsyncContainer]:
        """Create a temporary REQUEST scope.

        Yields:
            A REQUEST-scoped container for resolving services.
        """
        async with with_websocket_request(self._connection) as container:
            yield container


def provide_websocket_scope(socket: "WebSocket") -> WebSocketScope:
    """Litestar dependency provider for WebSocketScope.

    Args:
        socket: The WebSocket connection.

    Returns:
        A WebSocketScope factory for creating REQUEST scopes.
    """
    return WebSocketScope(socket)


__all__ = (
    "AsyncContainer",
    "Container",
    "Inject",
    "LitestarProvider",
    "LitestarRouter",
    "Provider",
    "QueryContext",
    "Scope",
    "WebSocketScope",
    "get_from_connection",
    "job_inject",
    "make_async_container",
    "make_container",
    "provide",
    "provide_websocket_scope",
    "query_id_var",
    "request_container_var",
    "setup_dishka",
    "with_websocket_request",
    "worker_container_var",
    "worker_scope",
)

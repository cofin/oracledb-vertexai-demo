"""Dependency injection utilities and clean imports.

This module provides a clean interface to the underlying DI framework
(Dishka) without exposing implementation details throughout the codebase.

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

from dishka.integrations.litestar import (
    FromDishka as Inject,
)
from dishka.integrations.litestar import (
    inject,
    setup_dishka,
)

__all__ = ("Inject", "inject", "setup_dishka")

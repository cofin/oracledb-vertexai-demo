from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import pytest

from app.domain.chat.services._adk import tools
from app.lib.di import Scope, request_container_var


def test_tools_module_exposes_set_app_container() -> None:
    assert hasattr(tools, "set_app_container")


@pytest.mark.anyio
async def test_tool_uses_app_container_request_scope_when_request_container_missing() -> None:
    class FakeToolsService:
        async def search_products_by_vector(
            self, query: str, limit: int, similarity_threshold: float
        ) -> dict[str, Any]:
            return {"query": query, "limit": limit, "threshold": similarity_threshold}

    class FakeRequestContainer:
        async def get(self, _dependency: object) -> FakeToolsService:
            return FakeToolsService()

    class FakeAppContainer:
        def __init__(self) -> None:
            self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        @asynccontextmanager
        async def __call__(self, *args: object, **kwargs: object):  # noqa: ANN204
            self.calls.append((args, kwargs))
            yield FakeRequestContainer()

    fake_app_container = FakeAppContainer()
    tools.set_app_container(fake_app_container)

    token = request_container_var.set(None)
    try:
        result = await tools.search_products_by_vector("pour-over beans", 5, 0.85)
    finally:
        request_container_var.reset(token)

    assert result == {"query": "pour-over beans", "limit": 5, "threshold": 0.85}
    assert len(fake_app_container.calls) == 1
    _, kwargs = fake_app_container.calls[0]
    assert kwargs.get("scope") == Scope.REQUEST

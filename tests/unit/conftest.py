from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from litestar import Litestar
from litestar.connection import ASGIConnection
from litestar.testing import AsyncTestClient

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar.types import ASGIApp, HTTPResponseStartEvent, HTTPScope, Receive, Scope, Send


@pytest.fixture
async def client(app: Litestar) -> AsyncGenerator[AsyncTestClient, None]:
    async with AsyncTestClient(app=app) as c:
        yield c


@pytest.fixture
def http_response_start() -> HTTPResponseStartEvent:
    return {
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"application/json")],
    }


@pytest.fixture
def http_response_body() -> dict[str, Any]:
    return {"type": "http.response.body", "body": b'{"hello": "world"}'}


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@pytest.fixture
def http_scope(state: dict[str, Any]) -> HTTPScope:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver")],
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
        "state": state,
    }


@pytest.fixture
def connection(http_scope: HTTPScope) -> ASGIConnection[Any, Any, Any]:
    async def receive() -> Any:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Any) -> None:
        pass

    return ASGIConnection[Any, Any, Any](scope=http_scope, receive=receive, send=send)
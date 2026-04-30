# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``POST /api/chat`` returns Jinja partial HTML for HTMX clients and JSON for SPA clients.

``ADKRunner`` is stubbed end-to-end so the test process does not need a live
Oracle session backend or a Vertex AI agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

pytestmark = pytest.mark.anyio

_FAKE_REPLY: dict[str, Any] = {
    "answer": "A pour-over Ethiopian Yirgacheffe brews bright and floral.",
    "search_metrics": {"total_ms": 42, "oracle_ms": 11, "embedding_ms": 30},
    "from_cache": False,
    "embedding_cache_hit": False,
    "intent_detected": "PRODUCT_RAG",
}


@pytest.fixture(autouse=True)
def _stub_adk_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``ADKRunner.__init__`` + ``process_request`` so DI never touches
    the real ADK ``Runner`` (which would require an Oracle session_service).
    """
    from app.domain.chat.services import ADKRunner

    def _noop_init(self: Any, *args: Any, **kwargs: Any) -> None:
        del args, kwargs
        self.session_service = None

    async def _stream_request(self: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: RUF029
        del self, args, kwargs
        yield {"type": "delta", "text": _FAKE_REPLY["answer"]}
        yield {"type": "final", **_FAKE_REPLY, "session_id": "stream-session", "response_time_ms": 42.0}

    monkeypatch.setattr(ADKRunner, "__init__", _noop_init)
    monkeypatch.setattr(ADKRunner, "process_request", AsyncMock(return_value=_FAKE_REPLY))
    monkeypatch.setattr(ADKRunner, "stream_request", _stream_request)


async def test_htmx_returns_partial(htmx_client: AsyncTestClient) -> None:
    from app.domain.chat.services import ADKRunner

    response = await htmx_client.post(
        "/api/chat",
        json={"message": "recommend an ethiopian", "persona": "enthusiast"},
        headers={"X-Session-Id": "client-controlled"},
    )
    assert response.status_code == 200, response.text[:500]
    body = response.text
    assert '<article class="message' in body, "HTMX branch must render the message bubble fragment"
    assert "<!DOCTYPE html>" not in body, "HTMX branch must not return a full page"
    call_kwargs = ADKRunner.process_request.await_args.kwargs  # type: ignore[attr-defined]
    assert call_kwargs["session_id"] != "client-controlled"
    assert call_kwargs["user_id"] == f"web:{call_kwargs['session_id']}"


async def test_htmx_validation_returns_chat_error(htmx_client: AsyncTestClient) -> None:
    response = await htmx_client.post("/api/chat", json={"message": "", "persona": "enthusiast"})
    assert response.status_code == 200, response.text[:500]
    assert response.headers.get("HX-Retarget") == "#chat-error"
    assert "chat_error" in response.text or "text-danger" in response.text


async def test_non_htmx_returns_json(client: AsyncTestClient) -> None:
    response = await client.post(
        "/api/chat",
        json={"message": "recommend an ethiopian", "persona": "enthusiast"},
    )
    assert response.status_code == 201, response.text[:500]
    payload = response.json()
    assert payload["answer"] == _FAKE_REPLY["answer"]
    assert payload["intentDetected"] == "PRODUCT_RAG"


async def test_stream_returns_sse_events(client: AsyncTestClient) -> None:
    response = await client.post(
        "/api/chat/stream",
        data={"message": "recommend an ethiopian", "persona": "enthusiast"},
    )

    assert response.status_code == 200, response.text[:500]
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: delta" in response.text
    assert "event: final" in response.text
    assert '"intent_detected": "PRODUCT_RAG"' in response.text

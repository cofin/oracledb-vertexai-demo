# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""The chat surface is two routes: ``POST /api/chat/stream`` (SSE) and
``POST /api/chat/session/clear``.

``ADKRunner`` is stubbed end-to-end so the test process does not need a live
Oracle session backend or a Vertex AI agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

pytestmark = [pytest.mark.anyio, pytest.mark.usefixtures("stub_adk_runner")]

_FAKE_REPLY: dict[str, Any] = {
    "answer": "A pour-over Ethiopian Yirgacheffe brews bright and floral.",
    "search_metrics": {"total_ms": 42, "oracle_ms": 11, "embedding_ms": 30, "vector_query": "ethiopian"},
    "embedding_cache_hit": True,
    "intent_detected": "PRODUCT_RAG",
    "sql_phases": [
        {
            "label": "Oracle vector search",
            "sql_key": "vector-search-products",
            "sql": "SELECT * FROM product WHERE VECTOR_DISTANCE(embedding, :query_vector, COSINE) > :threshold",
            "binds": {"query_vector": "<VECTOR[3072 FLOAT32], sha256=abc123, norm=1.0>", "threshold": 0.5},
            "row_count": 1,
            "runtime_ms": 11,
            "cache_status": "miss",
        }
    ],
}


@pytest.fixture
def stub_adk_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``ADKRunner.__init__`` + ``stream_request`` so DI never touches
    the real ADK ``Runner`` (which would require an Oracle session_service).
    """
    from app.domain.chat.services import ADKRunner

    def _noop_init(self: Any, *args: Any, **kwargs: Any) -> None:
        del args, kwargs
        self.session_service = None

    async def _stream_request(self: Any, *args: Any, **kwargs: Any) -> Any:
        del self, args, kwargs
        yield {"type": "delta", "text": _FAKE_REPLY["answer"]}
        yield {"type": "final", **_FAKE_REPLY, "session_id": "stream-session", "response_time_ms": 42.0}

    monkeypatch.setattr(ADKRunner, "__init__", _noop_init)
    monkeypatch.setattr(ADKRunner, "stream_request", _stream_request)
    monkeypatch.setattr(ADKRunner, "ensure_configured", staticmethod(lambda: None))


async def test_stream_returns_sse_events(client: AsyncTestClient) -> None:
    response = await client.post(
        "/api/chat/stream", data={"message": "recommend an ethiopian", "persona": "enthusiast"}
    )

    assert response.status_code == 200, response.text[:500]
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: delta" in response.text
    assert "event: final" in response.text
    assert '"intent_detected":"PRODUCT_RAG"' in response.text
    assert '"vector_query":"ethiopian"' in response.text
    assert '"embedding_cache_hit":true' in response.text
    assert '"sql_key":"vector-search-products"' in response.text
    assert "<VECTOR[3072 FLOAT32]" in response.text


async def test_stream_handles_runner_exception_after_response_started(
    client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.domain.chat.services import ADKRunner

    async def _broken_stream_request(self: Any, *args: Any, **kwargs: Any) -> Any:
        del self, args, kwargs
        yield {"type": "delta", "text": "Starting"}
        raise RuntimeError("tool exploded")

    monkeypatch.setattr(ADKRunner, "stream_request", _broken_stream_request)

    response = await client.post(
        "/api/chat/stream", data={"message": "recommend an ethiopian", "persona": "enthusiast"}
    )

    assert response.status_code == 200, response.text[:500]
    assert "event: delta" in response.text
    assert "event: error" in response.text
    assert "Chat failed while streaming. Please try again." in response.text
    assert "tool exploded" not in response.text


async def test_clear_chat_session_deletes_adk_session_and_resets_bridge(
    client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.domain.chat.services import ADKRunner

    calls: list[dict[str, str]] = []

    async def _clear_session(self: Any, **kwargs: str) -> None:
        del self
        calls.append(kwargs)

    monkeypatch.setattr(ADKRunner, "clear_session", _clear_session)

    response = await client.post("/api/chat/session/clear")

    assert response.status_code == 200, response.text[:500]
    assert response.json() == {"status": "cleared"}
    assert calls
    assert calls[0]["session_id"]
    assert calls[0]["user_id"] == f"web:{calls[0]['session_id']}"

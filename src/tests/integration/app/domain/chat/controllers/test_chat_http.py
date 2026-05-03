# SPDX-FileCopyrightText: 2026 Google LLC
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
    "search_metrics": {"total_ms": 42, "oracle_ms": 11, "embedding_ms": 30, "vector_query": "ethiopian"},
    "from_cache": False,
    "embedding_cache_hit": True,
    "intent_detected": "PRODUCT_RAG",
    "store_results": [],
    "inventory_results": [],
    "map_actions": [],
    "location_context": {},
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


@pytest.fixture(autouse=True)
def _stub_adk_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``ADKRunner.__init__`` + ``process_request`` so DI never touches
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
    monkeypatch.setattr(ADKRunner, "process_request", AsyncMock(return_value=_FAKE_REPLY))
    monkeypatch.setattr(ADKRunner, "stream_request", _stream_request)
    monkeypatch.setattr(ADKRunner, "ensure_configured", staticmethod(lambda: None))


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
    assert "Intent: PRODUCT_RAG" in body
    assert "Vector query: ethiopian" in body
    assert "Embedding phase: 30 ms" in body
    assert "Oracle vector phase: 11 ms" in body
    assert "embedding cache hit" in body
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
    assert payload["storeResults"] == []
    assert payload["inventoryResults"] == []
    assert payload["mapActions"] == []
    assert payload["locationContext"] == {}


async def test_json_location_context_requires_consent_for_coordinates(client: AsyncTestClient) -> None:
    from app.domain.chat.services import ADKRunner

    response = await client.post(
        "/api/chat",
        json={
            "message": "where can I pick up cold brew near me?",
            "persona": "enthusiast",
            "locationConsent": False,
            "latitude": 32.7876,
            "longitude": -96.7994,
            "city": "Dallas",
        },
    )

    assert response.status_code == 201, response.text[:500]
    call_kwargs = ADKRunner.process_request.await_args.kwargs  # type: ignore[attr-defined]
    assert call_kwargs["location_context"] == {"city": "Dallas"}


async def test_json_location_context_passes_consented_coordinates(client: AsyncTestClient) -> None:
    from app.domain.chat.services import ADKRunner

    response = await client.post(
        "/api/chat",
        json={
            "message": "where can I pick up cold brew near me?",
            "persona": "enthusiast",
            "locationConsent": True,
            "latitude": 32.7876,
            "longitude": -96.7994,
            "accuracy": 25,
        },
    )

    assert response.status_code == 201, response.text[:500]
    call_kwargs = ADKRunner.process_request.await_args.kwargs  # type: ignore[attr-defined]
    assert call_kwargs["location_context"] == {
        "coordinates": {"latitude": 32.7876, "longitude": -96.7994, "accuracy_meters": 25.0}
    }


async def test_json_location_context_rejects_invalid_consented_coordinates(client: AsyncTestClient) -> None:
    response = await client.post(
        "/api/chat",
        json={
            "message": "nearest store",
            "persona": "enthusiast",
            "locationConsent": True,
            "latitude": 120,
            "longitude": -96.7994,
        },
    )

    assert response.status_code == 400


async def test_non_htmx_ai_unconfigured_returns_503_without_exception_path(client: AsyncTestClient) -> None:
    from app.domain.chat.exceptions import AIServiceUnconfigured
    from app.domain.chat.services import ADKRunner

    ADKRunner.process_request.side_effect = AIServiceUnconfigured("AI service is not configured")  # type: ignore[attr-defined]

    response = await client.post(
        "/api/chat",
        json={"message": "recommend an ethiopian", "persona": "enthusiast"},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == 503
    assert payload["title"] == "AI service is not configured"


async def test_stream_returns_sse_events(client: AsyncTestClient) -> None:
    response = await client.post(
        "/api/chat/stream",
        data={"message": "recommend an ethiopian", "persona": "enthusiast"},
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
    client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain.chat.services import ADKRunner

    async def _broken_stream_request(self: Any, *args: Any, **kwargs: Any) -> Any:
        del self, args, kwargs
        yield {"type": "delta", "text": "Starting"}
        raise RuntimeError("tool exploded")

    monkeypatch.setattr(ADKRunner, "stream_request", _broken_stream_request)

    response = await client.post(
        "/api/chat/stream",
        data={"message": "recommend an ethiopian", "persona": "enthusiast"},
    )

    assert response.status_code == 200, response.text[:500]
    assert "event: delta" in response.text
    assert "event: error" in response.text
    assert "Chat failed while streaming. Please try again." in response.text
    assert "tool exploded" not in response.text


async def test_clear_chat_session_deletes_adk_session_and_resets_bridge(
    client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
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

# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Phase 4.7/4.9 contract: ``POST /api/chat`` returns Jinja partial HTML for
HTMX clients (``HX-Request: true``) and ``CoffeeChatReply`` JSON for SPA
clients.

These tests stub ``ADKRunner`` end-to-end (constructor + ``process_request``)
so the test process does NOT need a live Oracle session backend or a Vertex
AI agent — those paths are exercised in ``src/tests/integration``.
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
    "intent_detected": "RECOMMEND",
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

    monkeypatch.setattr(ADKRunner, "__init__", _noop_init)
    monkeypatch.setattr(ADKRunner, "process_request", AsyncMock(return_value=_FAKE_REPLY))


async def test_htmx_returns_partial(htmx_client: AsyncTestClient) -> None:
    response = await htmx_client.post(
        "/api/chat",
        json={"message": "recommend an ethiopian", "persona": "enthusiast"},
    )
    assert response.status_code == 200, response.text[:500]
    body = response.text
    assert '<article class="message' in body, "HTMX branch must render the message bubble fragment"
    assert "<!DOCTYPE html>" not in body, "HTMX branch must not return a full page"


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
    assert payload["intentDetected"] == "RECOMMEND"

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""The chat surface routes: POST /api/chat/stream and POST /api/chat/session/clear."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

pytestmark = [pytest.mark.anyio, pytest.mark.usefixtures("stub_orchestrator")]


@pytest.fixture
def stub_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub AgentOrchestrationService streaming and clearing for HTTP testing."""
    from app.domain.ai.services import AgentOrchestrationService

    async def _mock_stream(self: Any, *args: Any, **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        del self, args, kwargs
        yield {"type": "session", "session_id": "test-session-id"}
        yield {"type": "delta", "text": "A pour-over Ethiopian Yirgacheffe brews bright and floral."}
        yield {
            "type": "final",
            "session_id": "test-session-id",
            "search_metrics": {"prompt_tokens": 12, "output_tokens": 42, "total_tokens": 54},
        }

    async def _mock_clear(self: Any, *args: Any, **kwargs: Any) -> None:
        del self, args, kwargs

    monkeypatch.setattr(AgentOrchestrationService, "stream_conversation_turn", _mock_stream)
    monkeypatch.setattr(AgentOrchestrationService, "clear_session", _mock_clear)


async def test_stream_returns_sse_events(client: AsyncTestClient) -> None:
    """Verify that POST /api/chat/stream returns normalized SSE frames."""
    response = await client.post("/api/chat/stream", data={"message": "recommend an ethiopian", "persona": "barista"})

    assert response.status_code == 200, response.text[:500]
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: session" in response.text
    assert "event: delta" in response.text
    assert "event: final" in response.text
    assert "Ethiopian Yirgacheffe" in response.text


async def test_stream_handles_runtime_exception(client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that stream errors yield an error SSE frame rather than HTTP 500."""
    from app.domain.ai.services import AgentOrchestrationService

    async def _failing_stream(self: Any, *args: Any, **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        del self, args, kwargs
        yield {"type": "delta", "text": "Starting"}
        raise RuntimeError("simulated model failure")

    monkeypatch.setattr(AgentOrchestrationService, "stream_conversation_turn", _failing_stream)

    response = await client.post("/api/chat/stream", data={"message": "recommend an ethiopian", "persona": "barista"})

    assert response.status_code == 200, response.text[:500]
    assert "event: delta" in response.text
    assert "event: error" in response.text
    assert "Chat failed while streaming. Please try again." in response.text


async def test_clear_chat_session(client: AsyncTestClient) -> None:
    """Verify POST /api/chat/session/clear succeeds and clears session identity."""
    response = await client.post("/api/chat/session/clear")
    assert response.status_code == 200
    assert response.json() == {"status": "cleared"}

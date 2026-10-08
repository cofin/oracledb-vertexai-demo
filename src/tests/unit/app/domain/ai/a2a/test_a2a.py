# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for A2A 1.0 protocol endpoints and executor."""

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.context import ServerCallContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role, SendMessageRequest
from dishka import AsyncContainer
from litestar.stores.memory import MemoryStore
from litestar.testing import AsyncTestClient

from app.domain.ai.a2a.executor import CoffeeAgentExecutor
from app.domain.ai.services.agent_service import AgentOrchestrationService
from app.server.asgi import create_app


@pytest.mark.anyio
async def test_agent_card_discovery() -> None:
    """Verify GET /.well-known/agent-card.json returns valid card metadata with caching headers."""
    app = create_app()
    app.stores._stores["sessions"] = MemoryStore()

    async with AsyncTestClient(app=app) as client:
        response = await client.get("/.well-known/agent-card.json")
        assert response.status_code == 200
        card = response.json()
        assert card["name"] == "Cymbal Coffee Barista Agent"
        assert card["version"] == "1.0.0"
        assert len(card["skills"]) >= 2
        etag = response.headers.get("etag")
        assert etag is not None

        cached_response = await client.get("/.well-known/agent-card.json", headers={"if-none-match": etag})
        assert cached_response.status_code == 304


@pytest.mark.anyio
async def test_coffee_agent_executor_execution() -> None:
    """Verify CoffeeAgentExecutor processes messages and enqueues the agent response."""

    async def fake_stream(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        del args, kwargs
        yield {"type": "session", "session_id": "sess-1"}
        yield {"type": "delta", "text": "Pour-over brews "}
        yield {"type": "delta", "text": "clean and bright."}
        yield {"type": "final", "session_id": "sess-1"}

    mock_orchestrator = MagicMock(spec=AgentOrchestrationService)
    mock_orchestrator.stream_conversation_turn = fake_stream

    mock_req_container = AsyncMock()
    mock_req_container.get.return_value = mock_orchestrator

    mock_container = MagicMock(spec=AsyncContainer)
    mock_container.parent_container = None
    mock_container.return_value.__aenter__.return_value = mock_req_container

    executor = CoffeeAgentExecutor(container=mock_container)

    incoming_message = Message(role=Role.ROLE_USER, parts=[Part(text="How does pour-over taste?")])
    call_context = ServerCallContext()
    context = RequestContext(
        call_context=call_context,
        request=SendMessageRequest(message=incoming_message),
        context_id="test-session-123",
        task_id="task-456",
    )

    class RecordingQueue(EventQueue):
        """Test event queue recording enqueued items."""

        def __init__(self) -> None:
            self.events: list[Any] = []

        async def enqueue_event(self, event: Any) -> None:
            self.events.append(event)

    queue = RecordingQueue()
    await executor.execute(context, queue)

    assert len(queue.events) == 1
    result_event = queue.events[0]
    assert isinstance(result_event, Message)
    assert result_event.role == Role.ROLE_AGENT
    assert result_event.parts[0].text == "Pour-over brews clean and bright."

    await executor.cancel(context, queue)

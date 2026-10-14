# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for A2A 1.0 protocol endpoints and executor."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.context import ServerCallContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    Message,
    Part,
    Role,
    SendMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from dishka import AsyncContainer
from litestar.stores.memory import MemoryStore
from litestar.testing import AsyncTestClient

from app.domain.ai.a2a import COFFEE_AGENT_CARD, CoffeeAgentExecutor, build_a2a_call_context, build_agent_card
from app.domain.ai.services.agent_service import AgentOrchestrationService
from app.server.asgi import create_app


class _UnauthenticatedSentinel:
    """Stub unauthenticated user object without __str__ override."""


class _RecordingQueue(EventQueue):
    """Test event queue recording enqueued items."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    async def enqueue_event(self, event: Any) -> None:
        self.events.append(event)


def test_build_agent_card_custom_base_url() -> None:
    """Verify build_agent_card normalizes base_url and appends /a2a."""
    card = build_agent_card(base_url="https://coffee.example.com/")
    assert card.supported_interfaces[0].url == "https://coffee.example.com/a2a"
    assert COFFEE_AGENT_CARD.supported_interfaces[0].url == "http://localhost:8000/a2a"


@pytest.mark.anyio
async def test_build_a2a_call_context_deterministic_anonymous_owner_and_session_header() -> None:
    """Verify two unauthenticated requests resolve identical 'anonymous' owner scope in InMemoryTaskStore."""
    mock_container = MagicMock(spec=AsyncContainer)
    req_one = MagicMock()
    req_one.scope = {"user": _UnauthenticatedSentinel(), "auth": None, "state": {"dishka_container": mock_container}}
    req_one.headers = {"x-session-id": "custom-sess-99"}

    req_two = MagicMock()
    req_two.scope = {"user": _UnauthenticatedSentinel(), "auth": None, "state": {"dishka_container": mock_container}}
    req_two.headers = {}

    ctx_one = build_a2a_call_context(req_one)
    ctx_two = build_a2a_call_context(req_two)

    assert ctx_one.user.user_name == "anonymous"
    assert ctx_two.user.user_name == "anonymous"
    assert ctx_one.state["user_id"] == "anonymous"
    assert ctx_one.state["session_id"] == "custom-sess-99"
    assert ctx_one.state["dishka_container"] is mock_container

    store = InMemoryTaskStore()
    sample_task = Task(
        id="task-owner-test", context_id="custom-sess-99", status=TaskStatus(state=TaskState.TASK_STATE_WORKING)
    )
    await store.save(sample_task, ctx_one)
    loaded = await store.get("task-owner-test", ctx_two)
    assert loaded is not None
    assert loaded.id == "task-owner-test"


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
    """Verify CoffeeAgentExecutor processes messages through TaskUpdater and honours X-Session-ID."""
    captured_turns: list[dict[str, Any]] = []

    async def fake_stream(**kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        captured_turns.append(kwargs)
        yield {"type": "session", "session_id": kwargs["session_id"]}
        yield {"type": "delta", "text": "Pour-over brews "}
        yield {"type": "delta", "text": "clean and bright."}
        yield {"type": "final", "session_id": kwargs["session_id"]}

    mock_orchestrator = MagicMock(spec=AgentOrchestrationService)
    mock_orchestrator.stream_conversation_turn = fake_stream

    mock_req_container = AsyncMock()
    mock_req_container.get.return_value = mock_orchestrator

    mock_container = MagicMock(spec=AsyncContainer)
    mock_container.parent_container = None
    mock_container.return_value.__aenter__.return_value = mock_req_container

    executor = CoffeeAgentExecutor()

    incoming_message = Message(role=Role.ROLE_USER, parts=[Part(text="How does pour-over taste?")])
    call_context = ServerCallContext(
        state={"dishka_container": mock_container, "session_id": "hdr-session-777", "user_id": "anonymous"}
    )
    context = RequestContext(
        call_context=call_context,
        request=SendMessageRequest(message=incoming_message),
        context_id="test-session-123",
        task_id="task-456",
    )

    queue = _RecordingQueue()
    await executor.execute(context, queue)

    assert len(captured_turns) == 1
    assert captured_turns[0]["session_id"] == "hdr-session-777"
    assert captured_turns[0]["user_id"] == "anonymous"

    status_events = [e for e in queue.events if isinstance(e, TaskStatusUpdateEvent)]
    artifact_events = [e for e in queue.events if isinstance(e, TaskArtifactUpdateEvent)]
    assert status_events[0].status.state == TaskState.TASK_STATE_WORKING
    assert status_events[-1].status.state == TaskState.TASK_STATE_COMPLETED
    assert status_events[-1].status.message.parts[0].text == "Pour-over brews clean and bright."
    assert len(artifact_events) == 1
    assert artifact_events[0].artifact.parts[0].text == "Pour-over brews clean and bright."

    cancel_queue = _RecordingQueue()
    await executor.cancel(context, cancel_queue)
    assert isinstance(cancel_queue.events[0], TaskStatusUpdateEvent)
    assert cancel_queue.events[0].status.state == TaskState.TASK_STATE_CANCELED


@pytest.mark.anyio
async def test_coffee_agent_executor_missing_container_raises() -> None:
    """Verify CoffeeAgentExecutor raises RuntimeError instead of leaking a fallback container."""
    executor = CoffeeAgentExecutor()
    incoming_message = Message(role=Role.ROLE_USER, parts=[Part(text="Hello")])
    context = RequestContext(
        call_context=ServerCallContext(state={}),
        request=SendMessageRequest(message=incoming_message),
        context_id="sess-err",
        task_id="task-err",
    )
    with pytest.raises(RuntimeError, match="Dishka AsyncContainer is not available"):
        await executor.execute(context, MagicMock(spec=EventQueue))

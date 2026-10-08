# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for AgentRuntime execution loop, SSE stream adapter, and orchestration."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.ai.runtime import (
    AgentEvent,
    AgentLimits,
    AgentRuntime,
    AgentSpec,
    AgentStreamService,
    CallContext,
    Content,
    FunctionCall,
    Part,
    SpecTree,
    Tool,
    Usage,
    build_tool_preview,
)
from app.domain.ai.services import AgentOrchestrationService

pytestmark = pytest.mark.anyio


def test_build_tool_preview_normal_and_truncated() -> None:
    """Verify tool preview builds correct status and character-bounded previews."""
    ok_resp = {"items": ["espresso", "cortado"]}
    status, preview = build_tool_preview(ok_resp, max_chars=100)
    assert status == "completed"
    assert "espresso" in preview

    err_resp = {"error": {"code": "not_found", "message": "Store is closed"}}
    status, preview = build_tool_preview(err_resp, max_chars=100)
    assert status == "error"
    assert "not_found" in preview

    large_resp = {"data": "x" * 500}
    status, preview = build_tool_preview(large_resp, max_chars=20)
    assert status == "completed"
    assert len(preview) == 20
    assert preview.endswith("…")


async def test_agent_runtime_text_only_turn() -> None:
    """Verify AgentRuntime executes a text-only conversation turn without tool calls."""
    mock_model_client = MagicMock()

    async def mock_generate_stream(*args: Any, **kwargs: Any) -> Any:
        yield AgentEvent(
            session_id="s1",
            invocation_id="inv1",
            content=Content(role="model", parts=[Part(text="Welcome to Cymbal Coffee!")]),
            partial=False,
            usage=Usage(prompt_tokens=10, output_tokens=15, total_tokens=25),
        )

    mock_model_client.generate_stream = mock_generate_stream
    runtime = AgentRuntime(model_client=mock_model_client)

    root = AgentSpec(
        name="greeter",
        description="Greets customers",
        model="gemini-3.8-flash",
        static_instruction="You are a friendly host.",
    )
    tree = SpecTree(root=root)
    ctx = CallContext(session_id="s1", invocation_id="inv1", turn=1, state={})

    events = [
        ev
        async for ev in runtime.execute_turn(
            spec_tree=tree, session_id="s1", invocation_id="inv1", user_message="Hello", ctx=ctx
        )
    ]

    assert len(events) == 1
    assert events[0].text() == "Welcome to Cymbal Coffee!"
    assert events[0].session_id == "s1"
    assert events[0].agent == "greeter"


async def test_agent_runtime_tool_dispatch_and_recursion() -> None:
    """Verify AgentRuntime dispatches tools in parallel and re-invokes model with results."""
    mock_model_client = MagicMock()
    model_turn = 0

    async def mock_generate_stream(*args: Any, **kwargs: Any) -> Any:
        nonlocal model_turn
        model_turn += 1
        if model_turn == 1:
            fc = FunctionCall(id="call-lookup", name="lookup_menu", args={"category": "pourover"})
            yield AgentEvent(
                session_id="s1",
                invocation_id="inv1",
                content=Content(role="model", parts=[Part(function_call=fc)]),
                partial=False,
            )
        else:
            yield AgentEvent(
                session_id="s1",
                invocation_id="inv1",
                content=Content(role="model", parts=[Part(text="We have Ethiopian Yirgacheffe on pourover.")]),
                partial=False,
            )

    mock_model_client.generate_stream = mock_generate_stream

    async def lookup_menu(_ctx: CallContext, category: str) -> dict[str, Any]:
        return {"category": category, "coffee": "Ethiopian Yirgacheffe"}

    tool = Tool(
        name="lookup_menu",
        description="Lookup coffees by category",
        parameters_schema={"type": "OBJECT", "properties": {"category": {"type": "STRING"}}},
        param_types={"category": str},
        fn=lookup_menu,
    )

    root = AgentSpec(
        name="barista",
        description="Coffee expert",
        model="gemini-3.8-flash",
        static_instruction="You help with coffee orders.",
        tools=[tool],
    )
    tree = SpecTree(root=root)
    runtime = AgentRuntime(model_client=mock_model_client)
    ctx = CallContext(session_id="s1", invocation_id="inv1", turn=1, state={})

    events = [
        ev
        async for ev in runtime.execute_turn(
            spec_tree=tree,
            session_id="s1",
            invocation_id="inv1",
            user_message="What do you have for pourover?",
            ctx=ctx,
        )
    ]

    assert model_turn == 2
    assert any(ev.function_calls() for ev in events)
    assert any(ev.function_responses() for ev in events)
    assert events[-1].text() == "We have Ethiopian Yirgacheffe on pourover."


async def test_agent_runtime_tool_budget_exceeded() -> None:
    """Verify AgentRuntime halts turn when max tool calls per turn is exceeded."""
    mock_model_client = MagicMock()

    async def mock_generate_stream(*args: Any, **kwargs: Any) -> Any:
        fc = FunctionCall(id="c1", name="noop", args={})
        yield AgentEvent(
            session_id="s1",
            invocation_id="inv1",
            content=Content(role="model", parts=[Part(function_call=fc)]),
            partial=False,
        )

    mock_model_client.generate_stream = mock_generate_stream

    async def noop(_ctx: CallContext) -> dict[str, Any]:
        return {"ok": True}

    tool = Tool(
        name="noop",
        description="No-op tool",
        parameters_schema={"type": "OBJECT", "properties": {}},
        param_types={},
        fn=noop,
    )

    limits = AgentLimits(max_tool_calls_per_turn=2)
    runtime = AgentRuntime(model_client=mock_model_client, limits=limits)
    root = AgentSpec(
        name="tester",
        description="Tests limits",
        model="gemini-3.8-flash",
        static_instruction="Run loops.",
        tools=[tool],
    )
    tree = SpecTree(root=root)
    ctx = CallContext(session_id="s1", invocation_id="inv1", turn=1, state={})

    events = [
        ev
        async for ev in runtime.execute_turn(
            spec_tree=tree, session_id="s1", invocation_id="inv1", user_message="Loop", ctx=ctx
        )
    ]

    last_event = events[-1]
    assert last_event.finish_reason == "TOOL_LIMIT_EXCEEDED"
    assert "Tool execution limit reached" in last_event.text()


async def test_agent_stream_service_emits_session_deltas_final() -> None:
    """Verify AgentStreamService adapts AgentEvents into session, delta, and final frames."""
    adapter = AgentStreamService(ping_interval=10.0)

    async def sample_events() -> Any:
        yield AgentEvent(
            session_id="sess-100",
            invocation_id="inv-100",
            content=Content(role="model", parts=[Part(text="Hello")]),
            partial=True,
            usage=Usage(prompt_tokens=5, output_tokens=5, total_tokens=10),
        )
        yield AgentEvent(
            session_id="sess-100",
            invocation_id="inv-100",
            content=Content(role="model", parts=[Part(text=" world!")]),
            partial=False,
            usage=Usage(prompt_tokens=0, output_tokens=5, total_tokens=5),
        )

    frames = [frame async for frame in adapter.adapt(sample_events(), session_id="sess-100")]

    assert frames[0] == {"type": "session", "session_id": "sess-100"}
    deltas = [f for f in frames if f["type"] == "delta"]
    assert len(deltas) == 2
    assert deltas[0]["text"] == "Hello"
    assert deltas[1]["text"] == " world!"

    final_frame = frames[-1]
    assert final_frame["type"] == "final"
    assert final_frame["session_id"] == "sess-100"
    assert final_frame["search_metrics"]["total_tokens"] == 15


async def test_agent_stream_service_keepalive_ping() -> None:
    """Verify AgentStreamService emits ping frame during idle delays."""
    adapter = AgentStreamService(ping_interval=0.05)

    async def slow_events() -> Any:
        await asyncio.sleep(0.12)
        yield AgentEvent(
            session_id="sess-ping",
            invocation_id="inv-ping",
            content=Content(role="model", parts=[Part(text="Ready")]),
            partial=False,
        )

    frames = [frame async for frame in adapter.adapt(slow_events(), session_id="sess-ping")]

    ping_frames = [f for f in frames if f["type"] == "ping"]
    assert len(ping_frames) >= 1
    assert frames[-1]["type"] == "final"


async def test_agent_orchestration_service_flow() -> None:
    """Verify AgentOrchestrationService coordinates session check, execution, and persistence."""
    mock_runtime = MagicMock()
    mock_stream = AgentStreamService(ping_interval=10.0)
    mock_session_store = MagicMock()
    mock_session_store.get_session = AsyncMock(return_value=None)
    mock_session_store.save_session = AsyncMock(return_value=None)
    mock_session_store.clear_session = AsyncMock(return_value=None)

    mock_event_store = MagicMock()
    mock_event_store.list_events = AsyncMock(return_value=[])
    mock_event_store.append_event = AsyncMock(return_value=None)

    async def mock_execute_turn(*args: Any, **kwargs: Any) -> Any:
        yield AgentEvent(
            session_id="sess-orch",
            invocation_id="inv-orch",
            content=Content(role="model", parts=[Part(text="Order confirmed")]),
            partial=False,
        )

    mock_runtime.execute_turn = mock_execute_turn
    root_spec = AgentSpec(
        name="root", description="Coordinator", model="gemini-3.8-flash", static_instruction="Coordinate."
    )
    spec_tree = SpecTree(root=root_spec)

    service = AgentOrchestrationService(
        runtime=mock_runtime,
        stream_service=mock_stream,
        spec_tree=spec_tree,
        session_store=mock_session_store,
        event_store=mock_event_store,
    )

    frames = [
        f
        async for f in service.stream_conversation_turn(
            session_id="sess-orch", user_id="user-1", message="I'd like a cold brew"
        )
    ]

    assert mock_session_store.save_session.await_count == 1
    assert mock_event_store.append_event.await_count == 2
    assert frames[0]["type"] == "session"
    assert any(f["type"] == "delta" and f["text"] == "Order confirmed" for f in frames)
    assert frames[-1]["type"] == "final"

    await service.clear_session("sess-orch", "user-1")
    assert mock_session_store.clear_session.await_count == 1

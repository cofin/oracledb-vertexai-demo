# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for LitestarMCP 0.15 skill/prompt controllers, TurnBudget, AgentStreamFrame, and CoffeeToolContext."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from app.domain.ai.mcp import CoffeePromptController, CoffeeSkillController
from app.domain.ai.protocols import CoffeeToolContext, EventStoreProtocol, ModelClientProtocol, SessionStoreProtocol
from app.domain.ai.runtime import (
    AgentEvent,
    AgentRuntime,
    AgentSpec,
    AgentStreamFrame,
    CallContext,
    Content,
    FunctionCall,
    OracleEventStore,
    OracleSessionStore,
    Part,
    RunContextRegistry,
    SpanManager,
    SpecTree,
    TurnBudget,
    declare,
    to_agent_stream_frame,
)
from app.domain.products.services import MapsService


def test_coffee_skill_controller_exposes_skill_manifest_and_tools() -> None:
    """Verify CoffeeSkillController exposes cymbal-coffee-barista skill metadata and bound tools."""
    controller = CoffeeSkillController()
    skill = controller.to_agent_skill()

    assert skill["id"] == "cymbal-coffee-barista"
    assert skill["name"] == "cymbal-coffee-barista"
    assert "coffee" in skill["tags"]
    assert len(skill["examples"]) == 2
    assert "Cymbal Coffee" in controller.get_instructions()
    tools = controller.get_tools()
    assert [tool.name for tool in tools] == ["describe_barista_capabilities"]
    manifest = controller.describe_capabilities.fn(controller)
    assert manifest["skill"]["id"] == "cymbal-coffee-barista"
    assert "PRODUCT_RAG" in manifest["routes"]


def test_coffee_prompt_controller_renders_barista_and_inventory_prompts() -> None:
    """Verify CoffeePromptController renders barista-recommendation and store-inventory-check prompts."""
    controller = CoffeePromptController()

    assert controller.qualify_prompt_name("barista-recommendation") == "coffee/barista-recommendation"
    assert controller.qualify_prompt_name("store-inventory-check") == "coffee/store-inventory-check"

    rec_messages = controller.barista_recommendation.fn(
        controller, preference="fruity pour-over", dietary_notes="oat milk"
    )
    assert len(rec_messages) == 1
    rec_dict = rec_messages[0].to_mcp_dict()
    assert rec_dict["role"] == "user"
    assert "fruity pour-over" in rec_dict["content"]["text"]
    assert "oat milk" in rec_dict["content"]["text"]

    inv_messages = controller.store_inventory_check.fn(controller, product_name="Espresso Blend", city="Dallas")
    assert len(inv_messages) == 1
    inv_dict = inv_messages[0].to_mcp_dict()
    assert inv_dict["role"] == "user"
    assert "Espresso Blend" in inv_dict["content"]["text"]
    assert "Dallas" in inv_dict["content"]["text"]


def test_coffee_tool_context_and_protocols() -> None:
    """Verify CoffeeToolContext and runtime protocols wire services and stores cleanly."""
    product_svc = MagicMock()
    store_svc = MagicMock()
    inventory_svc = MagicMock()
    maps_svc = MapsService()
    embed_svc = MagicMock()
    turn_ctx = MagicMock()

    tool_ctx = CoffeeToolContext(
        product_service=product_svc,
        store_service=store_svc,
        inventory_service=inventory_svc,
        maps_service=maps_svc,
        embedding_service=embed_svc,
        turn_context=turn_ctx,
    )
    assert tool_ctx.vertex_ai_service is embed_svc
    assert tool_ctx.embedding_service is embed_svc
    assert tool_ctx.inventory_service is inventory_svc
    assert tool_ctx.maps_service is maps_svc
    assert tool_ctx.turn_context is turn_ctx

    registry = RunContextRegistry()
    call_ctx = CallContext(session_id="s-1", invocation_id="inv-1", turn=1, services=tool_ctx)
    token = registry.bind(call_ctx)
    resolved = registry.resolve(token)
    assert resolved.tool_context is tool_ctx
    registry.release(token)

    assert isinstance(OracleSessionStore(), SessionStoreProtocol)
    assert isinstance(OracleEventStore(), EventStoreProtocol)
    assert ModelClientProtocol is not None


@pytest.mark.anyio
async def test_turn_budget_enforces_max_tool_calls_and_frame_conversion() -> None:
    """Verify TurnBudget(max_turns=5, max_tool_calls=10) and AgentStreamFrame projection."""

    class _LoopingModelClient:
        async def generate_stream(
            self,
            contents: object,
            *,
            tools: object = None,
            system_instruction: str | None = None,
            model: str | None = None,
        ) -> AsyncIterator[AgentEvent]:
            del contents, tools, system_instruction, model
            calls = [Part(function_call=FunctionCall(name="noop_tool", args={}, id=f"call-{idx}")) for idx in range(6)]
            yield AgentEvent(
                session_id="s1", invocation_id="i1", content=Content(role="model", parts=calls), partial=False
            )

    def noop_tool(ctx: CallContext) -> dict[str, str]:
        del ctx
        return {"ok": "true"}

    budget = TurnBudget(max_turns=5, max_tool_calls=10)
    span_manager = SpanManager()
    runtime = AgentRuntime(model_client=_LoopingModelClient(), budget=budget, span_manager=span_manager)  # type: ignore[arg-type]
    assert runtime.budget is budget
    assert runtime.span_manager is span_manager

    spec = AgentSpec(
        name="test_agent",
        description="Test agent",
        model="gemini-3.8-flash",
        static_instruction="Follow test instructions.",
        tools=[declare(noop_tool)],
    )
    tree = SpecTree(root=spec)
    ctx = CallContext(session_id="s1", invocation_id="i1", turn=1)

    events = [
        ev
        async for ev in runtime.execute_turn(
            spec_tree=tree, session_id="s1", invocation_id="i1", user_message="run tools", ctx=ctx
        )
    ]
    assert any(ev.finish_reason == "TOOL_LIMIT_EXCEEDED" for ev in events)

    sse_frame = to_agent_stream_frame({"type": "final", "answer": "Fresh roast"}, turn_id="turn-1", seq=3)
    assert isinstance(sse_frame, AgentStreamFrame)
    assert sse_frame.event_type == "complete"
    assert sse_frame.turn_id == "turn-1"
    assert sse_frame.seq == 3
    assert sse_frame.text == "Fresh roast"

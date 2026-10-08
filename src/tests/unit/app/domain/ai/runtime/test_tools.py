# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for AI runtime primitives, schemas, CallContext, and tool runners."""

from typing import Any, Literal

import msgspec
import pytest

from app.domain.ai.runtime import (
    AgentEvent,
    AgentLimits,
    CallContext,
    Content,
    FunctionCall,
    FunctionResponse,
    Part,
    RunContextRegistry,
    Usage,
    declare,
    execute_parallel,
    translate_to_gemini_schema,
)

pytestmark = pytest.mark.anyio


class SearchFilter(msgspec.Struct, kw_only=True):
    """Filter struct for search tests."""

    category: str
    limit: int = 5


async def sample_search_tool(ctx: CallContext, query: str, limit: int = 10) -> dict[str, Any]:
    """Search catalog products.

    Args:
        ctx: Active CallContext.
        query: Search term.
        limit: Max products to return.

    Returns:
        Search results mapping.
    """
    return {"session": ctx.session_id, "query": query, "limit": limit, "items": [f"item-{i}" for i in range(limit)]}


async def structured_filter_tool(ctx: CallContext, filter_data: SearchFilter) -> dict[str, Any]:
    """Run search with nested filter struct.

    Args:
        ctx: Active CallContext.
        filter_data: SearchFilter struct.

    Returns:
        Structured result.
    """
    return {"category": filter_data.category, "limit": filter_data.limit}


def sync_calculator_tool(x: int, y: int) -> int:
    """Add two integers.

    Args:
        x: First int.
        y: Second int.

    Returns:
        Sum of x and y.
    """
    return x + y


async def failing_tool(ctx: CallContext) -> dict[str, Any]:
    """Tool that raises a runtime exception.

    Args:
        ctx: Active CallContext.

    Raises:
        ValueError: Always raises for testing error isolation.
    """
    raise ValueError("Database connection lost")


def test_translate_to_gemini_schema_primitives() -> None:
    """Verify conversion of primitive types to Gemini upper-case types."""
    raw = msgspec.json.schema(int)
    gemini = translate_to_gemini_schema(raw)
    assert gemini["type"] == "INTEGER"

    raw_str = msgspec.json.schema(str)
    assert translate_to_gemini_schema(raw_str)["type"] == "STRING"

    raw_bool = msgspec.json.schema(bool)
    assert translate_to_gemini_schema(raw_bool)["type"] == "BOOLEAN"

    raw_float = msgspec.json.schema(float)
    assert translate_to_gemini_schema(raw_float)["type"] == "NUMBER"


def test_translate_to_gemini_schema_optional_and_enum() -> None:
    """Verify handling of optional types and enum definitions."""
    raw_opt = msgspec.json.schema(str | None)
    gemini_opt = translate_to_gemini_schema(raw_opt)
    assert gemini_opt["type"] == "STRING"
    assert gemini_opt.get("nullable") is True

    raw_enum = msgspec.json.schema(Literal["light", "medium", "dark"])
    gemini_enum = translate_to_gemini_schema(raw_enum)
    assert set(gemini_enum["enum"]) == {"light", "medium", "dark"}


def test_translate_to_gemini_schema_nested_struct() -> None:
    """Verify nested Struct resolution without $ref keys in final output."""
    raw_struct = msgspec.json.schema(SearchFilter)
    gemini_struct = translate_to_gemini_schema(raw_struct)
    assert gemini_struct["type"] == "OBJECT"
    assert "properties" in gemini_struct
    assert gemini_struct["properties"]["category"]["type"] == "STRING"
    assert gemini_struct["properties"]["limit"]["type"] == "INTEGER"
    assert "$ref" not in gemini_struct


def test_call_context_and_registry() -> None:
    """Verify CallContext registration, resolution, and release lifecycle."""
    registry = RunContextRegistry()
    ctx = CallContext(session_id="session-123", invocation_id="inv-456", turn=1, state={"user": "tester"})
    token = registry.bind(ctx)
    assert isinstance(token, str)

    resolved = registry.resolve(token)
    assert resolved.session_id == "session-123"
    assert resolved.turn == 1

    registry.release(token)
    with pytest.raises(RuntimeError, match="Tool CallContext expired or missing"):
        registry.resolve(token)


def test_tool_declaration_generation() -> None:
    """Verify tool declaration extracts docstring, parameters, and types."""
    tool = declare(sample_search_tool)
    decl = tool.declaration()
    assert decl.name == "sample_search_tool"
    assert "Search catalog products" in decl.description
    assert decl.parameters_json_schema["type"] == "OBJECT"
    props = decl.parameters_json_schema["properties"]
    assert "query" in props
    assert props["query"]["type"] == "STRING"
    assert "limit" in props
    assert props["limit"]["type"] == "INTEGER"
    assert decl.parameters_json_schema["required"] == ["query"]


async def test_tool_invoke_with_coercion() -> None:
    """Verify automatic type coercion and execution of tools."""
    tool = declare(sample_search_tool)
    ctx = CallContext(session_id="sess-abc", invocation_id="inv-1", turn=2)

    result = await tool.invoke({"query": "ethiopian", "limit": "3"}, ctx)
    assert result["session"] == "sess-abc"
    assert result["limit"] == 3
    assert len(result["items"]) == 3


async def test_tool_invoke_struct_coercion() -> None:
    """Verify Struct argument coercion when passing nested dicts."""
    tool = declare(structured_filter_tool)
    ctx = CallContext(session_id="sess-xyz", invocation_id="inv-2", turn=1)

    result = await tool.invoke({"filter_data": {"category": "beans", "limit": 7}}, ctx)
    assert result["category"] == "beans"
    assert result["limit"] == 7


async def test_sync_tool_invoke() -> None:
    """Verify sync callable wrapping and return coercion."""
    tool = declare(sync_calculator_tool)
    ctx = CallContext(session_id="sess-1", invocation_id="inv-1", turn=1)

    result = await tool.invoke({"x": 15, "y": 27}, ctx)
    assert result == {"result": 42}


async def test_tool_invoke_validation_failure() -> None:
    """Verify invalid argument types return structured error."""
    tool = declare(structured_filter_tool)
    ctx = CallContext(session_id="sess-1", invocation_id="inv-1", turn=1)

    result = await tool.invoke({"filter_data": "not a struct"}, ctx)
    assert "error" in result
    assert result["error"]["code"] == "invalid_arguments"


async def test_execute_parallel_success_and_error_isolation() -> None:
    """Verify concurrent execution isolates tool failures and returns responses in order."""
    tools = {
        "search": declare(sample_search_tool, name="search"),
        "add": declare(sync_calculator_tool, name="add"),
        "failing": declare(failing_tool, name="failing"),
    }
    ctx = CallContext(session_id="sess-multi", invocation_id="inv-m", turn=3)

    calls = [
        FunctionCall(id="c1", name="search", args={"query": "latte", "limit": 2}),
        FunctionCall(id="c2", name="unknown", args={}),
        FunctionCall(id="c3", name="add", args={"x": 5, "y": 10}),
        FunctionCall(id="c4", name="failing", args={}),
    ]

    responses = await execute_parallel(calls, tools, ctx)
    assert len(responses) == 4

    assert responses[0].id == "c1"
    assert responses[0].name == "search"
    assert responses[0].response["limit"] == 2

    assert responses[1].id == "c2"
    assert responses[1].response["error"]["code"] == "unknown_tool"

    assert responses[2].id == "c3"
    assert responses[2].response == {"result": 15}

    assert responses[3].id == "c4"
    assert responses[3].response["error"]["code"] == "tool_failed"
    assert "ValueError" in responses[3].response["error"]["message"]


def test_agent_event_helpers() -> None:
    """Verify AgentEvent text and function call helper methods."""
    call = FunctionCall(id="fc1", name="search", args={"query": "espresso"})
    resp = FunctionResponse(id="fc1", name="search", response={"result": "found"})
    content = Content(
        role="model",
        parts=[
            Part(thought=True, text="thinking about espresso"),
            Part(text="Here is your espresso recommendation."),
            Part(function_call=call),
            Part(function_response=resp),
        ],
    )
    event = AgentEvent(
        session_id="s1",
        invocation_id="i1",
        content=content,
        usage=Usage(prompt_tokens=10, output_tokens=20, total_tokens=30),
    )

    assert event.text() == "Here is your espresso recommendation."
    assert event.function_calls() == [call]
    assert event.function_responses() == [resp]
    assert event.usage.total_tokens == 30


def test_agent_limits_defaults() -> None:
    """Verify default execution budget limits."""
    limits = AgentLimits()
    assert limits.max_tool_calls_per_turn == 8
    assert limits.max_model_calls_per_turn == 10
    assert limits.max_turns_per_session == 200
    assert limits.max_message_chars == 4000

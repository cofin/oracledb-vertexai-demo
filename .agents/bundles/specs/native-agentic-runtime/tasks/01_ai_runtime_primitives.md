---
type: Task
id: task-1
flow_id: native-agentic-runtime
state: closed
title: Implement Generic AI Runtime Primitives, Schemas, Tools, and CallContext
description: Build msgspec wire structs, Gemini FunctionDeclaration schema converter, declare() tool runner, execute_parallel(), and request-scoped CallContext in app.domain.ai.runtime.
verification_strategy: behavior_tdd
depends_on: []
commit: null
tags:
  - task
  - ai-runtime
  - msgspec
  - tools
  - schema
---

# Task task-1: Implement Generic AI Runtime Primitives, Schemas, Tools, and CallContext

## Objective
Establish the foundational type-safe primitives, JSON-to-Gemini schema translation, function tool decorator, concurrent tool runner, and request-scoped `CallContext` in `src/app/domain/ai/runtime/`.

## Itemized Checklist
- [x] Create `src/app/domain/ai/__init__.py` and `src/app/domain/ai/runtime/__init__.py`.
- [x] Implement `src/app/domain/ai/runtime/_types.py` with frozen `msgspec.Struct` wire contracts.
- [x] Implement `src/app/domain/ai/runtime/_schema.py` with `translate_to_gemini_schema()`.
- [x] Implement `src/app/domain/ai/runtime/_context.py` with `CallContext` and `RunContextRegistry`.
- [x] Implement `src/app/domain/ai/runtime/_tools.py` with `Tool`, `ToolDeclaration`, `declare()`, and `execute_parallel()`.
- [x] Export public runtime types from `src/app/domain/ai/runtime/__init__.py`.
- [x] Author test suite `src/tests/unit/app/domain/ai/runtime/test_tools.py` verifying schema conversion, argument coercion, and parallel execution.

## Implementation Details & Code Samples

### 1. `src/app/domain/ai/runtime/_types.py`
```python
"""Provider-neutral msgspec.Struct wire contracts for dynamic agents."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

import msgspec


class FunctionCall(msgspec.Struct, kw_only=True, frozen=True):
    """Tool call emitted by the model."""

    id: str = ""
    name: str
    args: dict[str, Any] = {}


class FunctionResponse(msgspec.Struct, kw_only=True, frozen=True):
    """Result returned by a tool execution."""

    id: str = ""
    name: str
    response: dict[str, Any]


class Part(msgspec.Struct, kw_only=True, frozen=True):
    """Single content segment within a message."""

    text: str | None = None
    thought: bool = False
    thought_signature: bytes | None = None
    function_call: FunctionCall | None = None
    function_response: FunctionResponse | None = None


class Content(msgspec.Struct, kw_only=True, frozen=True):
    """Role-tagged message content."""

    role: Literal["user", "model", "system"]
    parts: list[Part] = []


class Usage(msgspec.Struct, kw_only=True, frozen=True):
    """Token accounting counters."""

    prompt_tokens: int = 0
    output_tokens: int = 0
    thoughts_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0


class AgentLimits(msgspec.Struct, kw_only=True, frozen=True):
    """Per-turn and per-session execution budgets."""

    max_tool_calls_per_turn: int = 8
    max_model_calls_per_turn: int = 10
    max_turns_per_session: int = 200
    max_message_chars: int = 4000


class AgentEvent(msgspec.Struct, kw_only=True):
    """Sequenced event in the agent conversation log."""

    id: UUID = msgspec.field(default_factory=uuid4)
    session_id: str
    invocation_id: str
    seq: int = 0
    turn: int = 0
    agent: str = "assistant"
    content: Content | None = None
    partial: bool = False
    usage: Usage | None = None
    finish_reason: str | None = None
    actions: dict[str, Any] = msgspec.field(default_factory=dict)
    created_at: datetime = msgspec.field(default_factory=lambda: datetime.now(timezone.utc))

    def text(self) -> str:
        """Return non-thought text parts concatenated."""
        if self.content is None:
            return ""
        return "".join(p.text for p in self.content.parts if p.text and not p.thought)

    def function_calls(self) -> list[FunctionCall]:
        """Return all function calls present in this event."""
        if self.content is None:
            return []
        return [p.function_call for p in self.content.parts if p.function_call is not None]

    def function_responses(self) -> list[FunctionResponse]:
        """Return all function responses present in this event."""
        if self.content is None:
            return []
        return [p.function_response for p in self.content.parts if p.function_response is not None]
```

### 2. `src/app/domain/ai/runtime/_schema.py`
```python
"""JSON Schema to Gemini FunctionDeclaration schema translation."""

from typing import Any

GEMINI_ALLOWED_KEYS = frozenset(
    {
        "type",
        "format",
        "description",
        "nullable",
        "enum",
        "items",
        "properties",
        "required",
    }
)


def translate_to_gemini_schema(raw_schema: dict[str, Any]) -> dict[str, Any]:
    """Translate msgspec JSON Schema output into Gemini FunctionDeclaration schema subset."""
    defs = raw_schema.get("$defs", {})

    def _visit(node: Any) -> dict[str, Any]:
        if not isinstance(node, dict):
            return {"type": "STRING"}
        if "$ref" in node:
            ref_name = str(node["$ref"]).rsplit("/", maxsplit=1)[-1]
            resolved = defs.get(ref_name)
            return _visit(resolved) if isinstance(resolved, dict) else {"type": "OBJECT"}
        if "anyOf" in node:
            branches = [b for b in node["anyOf"] if isinstance(b, dict)]
            non_null = [b for b in branches if b.get("type") != "null"]
            has_null = len(non_null) != len(branches)
            merged = _visit(non_null[0]) if non_null else {"type": "STRING"}
            if has_null:
                merged["nullable"] = True
            return merged

        out: dict[str, Any] = {}
        for k, v in node.items():
            if k not in GEMINI_ALLOWED_KEYS:
                continue
            if k == "type" and isinstance(v, str):
                out["type"] = v.upper()
            elif k == "properties" and isinstance(v, dict):
                out["properties"] = {prop: _visit(spec) for prop, spec in v.items()}
            elif k == "items" and isinstance(v, dict):
                out["items"] = _visit(v)
            elif k == "enum" and isinstance(v, list):
                out["enum"] = [str(item) for item in v]
            else:
                out[k] = v
        out.setdefault("type", "OBJECT" if "properties" in out else "STRING")
        return out

    return _visit(raw_schema)
```

### 3. `src/app/domain/ai/runtime/_context.py`
```python
"""Request-scoped invocation context and registry for tool execution."""

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class CallContext:
    """Execution context passed into tool invocations."""

    session_id: str
    invocation_id: str
    turn: int
    state: dict[str, Any]
    services: Any = None


class RunContextRegistry:
    """Token-based registry mapping single-turn tokens to CallContext."""

    def __init__(self) -> None:
        self._contexts: dict[str, CallContext] = {}

    def bind(self, context: CallContext) -> str:
        """Bind a CallContext and return an opaque token."""
        token = uuid4().hex
        self._contexts[token] = context
        return token

    def resolve(self, token: str) -> CallContext:
        """Resolve a CallContext from an opaque token."""
        ctx = self._contexts.get(token)
        if ctx is None:
            msg = "Tool CallContext expired or missing"
            raise RuntimeError(msg)
        return ctx

    def release(self, token: str) -> None:
        """Release a bound token when the turn completes."""
        self._contexts.pop(token, None)
```

### 4. `src/app/domain/ai/runtime/_tools.py`
```python
"""Tool declaration, schema binding, and concurrent execution."""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

import msgspec

from app.domain.ai.runtime._context import CallContext
from app.domain.ai.runtime._schema import translate_to_gemini_schema
from app.domain.ai.runtime._types import FunctionCall, FunctionResponse


@dataclass(slots=True)
class ToolDeclaration:
    """Model-facing function declaration."""

    name: str
    description: str
    parameters_json_schema: dict[str, Any]


@dataclass(slots=True)
class Tool:
    """Executable function tool with argument validation."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    param_types: dict[str, Any]
    fn: Callable[..., Awaitable[dict[str, Any]]]

    def declaration(self) -> ToolDeclaration:
        """Return the Gemini-compatible ToolDeclaration."""
        return ToolDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=self.parameters_schema,
        )

    async def invoke(self, raw_args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
        """Validate arguments and invoke the wrapped coroutine."""
        coerced: dict[str, Any] = {}
        for key, value in raw_args.items():
            target_type = self.param_types.get(key)
            if target_type is not None and target_type is not Any:
                try:
                    coerced[key] = msgspec.convert(value, type=target_type, strict=False)
                except msgspec.ValidationError as exc:
                    return {"error": {"code": "invalid_arguments", "message": f"Invalid '{key}': {exc}"}}
            else:
                coerced[key] = value
        return await self.fn(ctx, **coerced)


def declare(
    handler: Callable[..., Any],
    *,
    name: str | None = None,
    description: str | None = None,
) -> Tool:
    """Inspect function signature and build a schema-validated Tool."""
    tool_name = name or handler.__name__
    tool_doc = description or inspect.getdoc(handler) or tool_name
    sig = inspect.signature(handler)
    hints = get_type_hints(handler)

    params = list(sig.parameters.values())
    first_is_ctx = bool(params) and hints.get(params[0].name) is CallContext
    user_params = params[1:] if first_is_ctx else params

    properties: dict[str, Any] = {}
    required: list[str] = []
    param_types: dict[str, Any] = {}

    for param in user_params:
        ann = hints.get(param.name, str)
        param_types[param.name] = ann
        prop_schema = translate_to_gemini_schema(msgspec.json.schema(ann))
        properties[param.name] = prop_schema
        if param.default is inspect.Parameter.empty:
            required.append(param.name)

    schema: dict[str, Any] = {"type": "OBJECT", "properties": properties}
    if required:
        schema["required"] = required

    async def _runner(ctx: CallContext, **kwargs: Any) -> dict[str, Any]:
        call_args = (ctx,) if first_is_ctx else ()
        if inspect.iscoroutinefunction(handler):
            res = await handler(*call_args, **kwargs)
        else:
            res = handler(*call_args, **kwargs)
        builtin = msgspec.to_builtins(res)
        return builtin if isinstance(builtin, dict) else {"result": builtin}

    return Tool(
        name=tool_name,
        description=tool_doc,
        parameters_schema=schema,
        param_types=param_types,
        fn=_runner,
    )


async def execute_parallel(
    calls: list[FunctionCall],
    tools: dict[str, Tool],
    ctx: CallContext,
) -> list[FunctionResponse]:
    """Execute model function calls concurrently via asyncio.gather()."""

    async def _run_one(call: FunctionCall) -> FunctionResponse:
        tool = tools.get(call.name)
        if tool is None:
            return FunctionResponse(
                id=call.id,
                name=call.name,
                response={"error": {"code": "unknown_tool", "message": f"Tool '{call.name}' is not registered."}},
            )
        try:
            output = await tool.invoke(call.args, ctx)
        except Exception as exc:
            output = {
                "error": {
                    "code": "tool_failed",
                    "message": f"{tool.name} failed ({type(exc).__name__}).",
                }
            }
        return FunctionResponse(id=call.id, name=call.name, response=output)

    results = await asyncio.gather(*(_run_one(c) for c in calls))
    return list(results)
```

## Verification
- Strategy: `behavior_tdd`
- Initial Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/runtime/test_tools.py`
  - Expected: Fails with `ModuleNotFoundError: No module named 'app.domain.ai'`
- Final Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/runtime/test_tools.py && make lint`
  - Expected: All unit tests pass, schemas match Gemini expectations, and `make lint` is clean.

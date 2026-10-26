# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tool declaration, schema binding, and concurrent execution."""

import asyncio
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast, get_type_hints

import msgspec

from app.domain.ai.runtime._context import CallContext
from app.domain.ai.runtime._schema import translate_to_gemini_schema
from app.domain.ai.runtime._types import FunctionCall, FunctionResponse

__all__ = ("Tool", "ToolDeclaration", "declare", "execute_parallel")


@dataclass(frozen=True, slots=True)
class ToolDeclaration:
    """Model-facing function declaration."""

    name: str
    description: str
    parameters_json_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Tool:
    """Executable function tool with argument validation."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    param_types: dict[str, Any]
    fn: Callable[..., Any]

    @property
    def input_schema(self) -> dict[str, Any]:
        """Tool input JSON schema."""
        return self.parameters_schema

    def declaration(self) -> ToolDeclaration:
        """Return the Gemini-compatible ToolDeclaration.

        Returns:
            ToolDeclaration with parameters schema.
        """
        return ToolDeclaration(
            name=self.name, description=self.description, parameters_json_schema=self.parameters_schema
        )

    async def invoke(self, raw_args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
        """Validate arguments and invoke the wrapped coroutine.

        Args:
            raw_args: Dictionary of raw uncoerced argument values.
            ctx: Active CallContext for the turn.

        Returns:
            Dictionary response from the tool execution or an error object.
        """
        coerced: dict[str, Any] = {}
        for key, value in raw_args.items():
            if key not in self.param_types:
                return {"error": {"code": "invalid_arguments", "message": f"Unexpected argument '{key}'"}}
            target_type = self.param_types.get(key)
            if target_type is not None and target_type is not Any:
                try:
                    coerced[key] = msgspec.convert(value, type=target_type, strict=False)
                except msgspec.ValidationError as exc:
                    return {"error": {"code": "invalid_arguments", "message": f"Invalid '{key}': {exc}"}}
            else:
                coerced[key] = value

        for req in self.input_schema.get("required", []):
            if req not in coerced:
                return {"error": {"code": "invalid_arguments", "message": f"Missing required argument '{req}'"}}

        res = self.fn(ctx, **coerced)
        if inspect.isawaitable(res):
            awaited_res = await res
            return cast(dict[str, Any], awaited_res)
        return cast(dict[str, Any], res)


def declare(handler: Callable[..., Any], *, name: str | None = None, description: str | None = None) -> Tool:
    """Inspect function signature and build a schema-validated Tool.

    Args:
        handler: Callable implementing the tool.
        name: Optional override name for the tool.
        description: Optional override description.

    Returns:
        Configured Tool instance.
    """
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

    schema: dict[str, Any] = {"type": "object", "properties": properties}
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

    return Tool(name=tool_name, description=tool_doc, parameters_schema=schema, param_types=param_types, fn=_runner)


async def execute_parallel(
    calls: list[FunctionCall], tools: dict[str, Tool], ctx: CallContext
) -> list[FunctionResponse]:
    """Execute model function calls concurrently via asyncio.gather().

    Args:
        calls: List of FunctionCall objects requested by the model.
        tools: Mapping of registered tool names to Tool instances.
        ctx: Active CallContext for the turn.

    Returns:
        List of FunctionResponse objects corresponding to the input calls.
    """

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
            output = {"error": {"code": "tool_failed", "message": f"{tool.name} failed ({type(exc).__name__})."}}
        return FunctionResponse(id=call.id, name=call.name, response=output)

    results = await asyncio.gather(*(_run_one(c) for c in calls))
    return list(results)

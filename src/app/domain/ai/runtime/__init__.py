# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Core primitives, types, schema translation, and tool runners for dynamic agents."""

from ._context import CallContext, CoffeeToolContext, RunContextRegistry
from ._loop import AgentRuntime, BudgetExceededError, SpanManager, TurnBudget
from ._model import GeminiModelClient
from ._schema import GEMINI_ALLOWED_KEYS, translate_to_gemini_schema
from ._spec import AgentSpec, GenerationConfig, SpecTree, fence_context_block
from ._store import OracleEventStore, OracleSessionStore
from ._stream import AgentStreamFrame, AgentStreamService, build_tool_preview, to_agent_stream_frame
from ._tools import Tool, ToolDeclaration, declare, execute_parallel
from ._types import AgentEvent, AgentLimits, Content, FunctionCall, FunctionResponse, Part, Usage

__all__ = (
    "GEMINI_ALLOWED_KEYS",
    "AgentEvent",
    "AgentLimits",
    "AgentRuntime",
    "AgentSpec",
    "AgentStreamFrame",
    "AgentStreamService",
    "BudgetExceededError",
    "CallContext",
    "CoffeeToolContext",
    "Content",
    "FunctionCall",
    "FunctionResponse",
    "GeminiModelClient",
    "GenerationConfig",
    "OracleEventStore",
    "OracleSessionStore",
    "Part",
    "RunContextRegistry",
    "SpanManager",
    "SpecTree",
    "Tool",
    "ToolDeclaration",
    "TurnBudget",
    "Usage",
    "build_tool_preview",
    "declare",
    "execute_parallel",
    "fence_context_block",
    "to_agent_stream_frame",
    "translate_to_gemini_schema",
)

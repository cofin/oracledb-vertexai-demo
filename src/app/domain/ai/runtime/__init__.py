# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Core primitives, types, schema translation, and tool runners for dynamic agents."""

from ._context import CallContext, RunContextRegistry
from ._loop import AgentRuntime
from ._model import GeminiModelClient
from ._schema import GEMINI_ALLOWED_KEYS, translate_to_gemini_schema
from ._spec import AgentSpec, GenerationConfig, SpecTree, fence_context_block
from ._store import OracleEventStore, OracleSessionStore
from ._stream import AgentStreamService, build_tool_preview
from ._tools import Tool, ToolDeclaration, declare, execute_parallel
from ._types import AgentEvent, AgentLimits, Content, FunctionCall, FunctionResponse, Part, Usage

__all__ = (
    "GEMINI_ALLOWED_KEYS",
    "AgentEvent",
    "AgentLimits",
    "AgentRuntime",
    "AgentSpec",
    "AgentStreamService",
    "CallContext",
    "Content",
    "FunctionCall",
    "FunctionResponse",
    "GeminiModelClient",
    "GenerationConfig",
    "OracleEventStore",
    "OracleSessionStore",
    "Part",
    "RunContextRegistry",
    "SpecTree",
    "Tool",
    "ToolDeclaration",
    "Usage",
    "build_tool_preview",
    "declare",
    "execute_parallel",
    "fence_context_block",
    "translate_to_gemini_schema",
)

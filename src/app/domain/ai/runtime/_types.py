# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Provider-neutral msgspec.Struct wire contracts for dynamic agents."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

import msgspec

__all__ = ("AgentEvent", "AgentLimits", "Content", "FunctionCall", "FunctionResponse", "Part", "Usage")


class FunctionCall(msgspec.Struct, kw_only=True, frozen=True):
    """Tool call emitted by the model."""

    name: str
    id: str = ""
    args: dict[str, Any] = {}


class FunctionResponse(msgspec.Struct, kw_only=True, frozen=True):
    """Result returned by a tool execution."""

    name: str
    response: dict[str, Any]
    id: str = ""


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

    session_id: str
    invocation_id: str
    id: UUID = msgspec.field(default_factory=uuid4)
    seq: int = 0
    turn: int = 0
    agent: str = "assistant"
    content: Content | None = None
    partial: bool = False
    usage: Usage | None = None
    finish_reason: str | None = None
    actions: dict[str, Any] = msgspec.field(default_factory=dict)
    created_at: datetime = msgspec.field(default_factory=lambda: datetime.now(UTC))

    def text(self) -> str:
        """Return non-thought text parts concatenated.

        Returns:
            Concatenated text from all non-thought parts.
        """
        if self.content is None:
            return ""
        return "".join(p.text for p in self.content.parts if p.text and not p.thought)

    def function_calls(self) -> list[FunctionCall]:
        """Return all function calls present in this event.

        Returns:
            List of function calls from parts.
        """
        if self.content is None:
            return []
        return [p.function_call for p in self.content.parts if p.function_call is not None]

    def function_responses(self) -> list[FunctionResponse]:
        """Return all function responses present in this event.

        Returns:
            List of function responses from parts.
        """
        if self.content is None:
            return []
        return [p.function_response for p in self.content.parts if p.function_response is not None]

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Runtime protocol definitions for agent persistence, model clients, and tool context."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from app.domain.ai.runtime._context import CoffeeToolContext

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    from app.domain.ai.runtime._tools import ToolDeclaration
    from app.domain.ai.runtime._types import AgentEvent, Content

__all__ = ("CoffeeToolContext", "EventStoreProtocol", "ModelClientProtocol", "SessionStoreProtocol")


@runtime_checkable
class SessionStoreProtocol(Protocol):
    """Protocol for agent session state persistence."""

    async def get_session(self, session_id: str, user_id: str) -> dict[str, Any] | None:
        """Fetch session state for a session and user."""
        ...

    async def save_session(self, session_id: str, user_id: str, app_name: str, state: dict[str, Any]) -> None:
        """Create or update a persisted session record."""
        ...

    async def clear_session(self, session_id: str, user_id: str) -> None:
        """Delete session state and associated events."""
        ...


@runtime_checkable
class EventStoreProtocol(Protocol):
    """Protocol for ordered agent conversation event persistence."""

    async def get_next_seq(self, session_id: str) -> int:
        """Return the next monotonic event sequence number for a session."""
        ...

    async def append_event(self, event: AgentEvent) -> None:
        """Persist a single AgentEvent row."""
        ...

    async def list_events(self, session_id: str, limit: int = 100) -> list[AgentEvent]:
        """List ordered AgentEvent rows for a session."""
        ...


@runtime_checkable
class ModelClientProtocol(Protocol):
    """Protocol for streaming model clients."""

    def generate_stream(
        self,
        contents: Sequence[Content],
        *,
        tools: Sequence[ToolDeclaration] | None = None,
        system_instruction: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Stream AgentEvent chunks for a conversation turn."""
        ...

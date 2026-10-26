# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle SQLSpec persistence stores for AI conversation sessions and event streams."""

from __future__ import annotations

from typing import Any

from app.domain.ai.runtime._types import AgentEvent, Content
from app.lib.service import OracleLoaderService
from app.utils.serialization import decode_json, encode_json, to_schema

__all__ = ("OracleEventStore", "OracleSessionStore")


class OracleSessionStore(OracleLoaderService):
    """Oracle 26ai backed session state store."""

    __slots__ = ()

    async def get_session(self, session_id: str, user_id: str) -> dict[str, Any] | None:
        """Fetch session metadata and state dictionary.

        Args:
            session_id: Unique session identifier.
            user_id: Owner user identifier.

        Returns:
            Dictionary with session row or None if not found.
        """
        async with self.provide_app_session() as driver:
            return await driver.select_one_or_none(
                self.get_sql("get-ai-session"), session_id=session_id, user_id=user_id
            )

    async def save_session(self, session_id: str, user_id: str, app_name: str, state: dict[str, Any]) -> None:
        """Upsert session metadata and state JSON document and commit.

        Args:
            session_id: Unique session identifier.
            user_id: Owner user identifier.
            app_name: Name of the hosting application.
            state: Serialized session state dictionary.
        """
        encoded_state = encode_json(state)
        async with self.provide_app_session() as driver:
            await driver.execute(
                self.get_sql("upsert-ai-session"),
                session_id=session_id,
                user_id=user_id,
                app_name=app_name,
                state=encoded_state,
            )
            await driver.commit()

    async def clear_session(self, session_id: str, user_id: str) -> None:
        """Delete session and associated history rows and commit.

        Args:
            session_id: Unique session identifier.
            user_id: Owner user identifier.
        """
        async with self.provide_app_session() as driver:
            await driver.execute(self.get_sql("clear-ai-session"), session_id=session_id, user_id=user_id)
            await driver.commit()


class OracleEventStore(OracleLoaderService):
    """Oracle 26ai backed event log store."""

    __slots__ = ()

    async def get_next_seq(self, session_id: str) -> int:
        """Return the next monotonic event sequence number for a session.

        Args:
            session_id: Unique session identifier.

        Returns:
            Positive integer sequence number starting at 1.
        """
        async with self.provide_app_session() as driver:
            val = await driver.select_value_or_none(self.get_sql("next-ai-event-seq"), session_id=session_id)
            return int(val) if val is not None else 1

    async def append_event(self, event: AgentEvent) -> None:
        """Insert a monotonic event row into Oracle persistence and commit.

        Args:
            event: AgentEvent instance to record.
        """
        encoded_content = encode_json(event.content) if event.content is not None else None
        encoded_actions = encode_json(event.actions)
        async with self.provide_app_session() as driver:
            await driver.execute(
                self.get_sql("append-ai-event"),
                session_id=event.session_id,
                invocation_id=event.invocation_id,
                seq=event.seq,
                turn=event.turn,
                agent=event.agent,
                content=encoded_content,
                actions=encoded_actions,
            )
            await driver.commit()

    async def list_events(self, session_id: str, limit: int = 100) -> list[AgentEvent]:
        """Fetch ordered history events for a given session.

        Args:
            session_id: Unique session identifier.
            limit: Maximum number of most-recent events to return in chronological order.

        Returns:
            Chronological list of AgentEvent instances.
        """
        bounded_limit = max(1, limit)
        async with self.provide_app_session() as driver:
            rows = await driver.select(self.get_sql("list-ai-events"), session_id=session_id, limit=bounded_limit)
        return [_row_to_agent_event(row) for row in rows]


def _row_to_agent_event(row: dict[str, Any]) -> AgentEvent:
    """Decode an Oracle agent_event row mapping into a typed AgentEvent."""
    content: Content | None = None
    raw_content = row.get("content")
    if isinstance(raw_content, str | bytes | bytearray):
        content = decode_json(raw_content, target_type=Content)
    elif isinstance(raw_content, dict):
        content = to_schema(raw_content, Content)

    actions: dict[str, Any] = {}
    raw_actions = row.get("actions")
    if isinstance(raw_actions, str | bytes | bytearray):
        actions = decode_json(raw_actions, target_type=dict[str, Any])
    elif isinstance(raw_actions, dict):
        actions = dict(raw_actions)

    return AgentEvent(
        session_id=str(row.get("session_id", "")),
        invocation_id=str(row.get("invocation_id", "")),
        agent=str(row.get("agent", "")),
        content=content,
        actions=actions,
        seq=int(row.get("seq", 0)),
        turn=int(row.get("turn", 0)),
        partial=False,
    )

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle SQLSpec persistence stores for AI conversation sessions and event streams."""

from typing import Any

import msgspec
from sqlspec.adapters.oracledb import OracleAsyncDriver

from app.config import db_manager
from app.domain.ai.runtime._types import AgentEvent, Content

__all__ = ("OracleEventStore", "OracleSessionStore")


class OracleSessionStore:
    """Oracle 26ai backed session state store."""

    def __init__(self, driver: OracleAsyncDriver) -> None:
        """Initialize session store with Oracle async driver.

        Args:
            driver: SQLSpec OracleAsyncDriver instance.
        """
        self._driver = driver

    async def get_session(self, session_id: str, user_id: str) -> dict[str, object] | None:
        """Fetch session metadata and state dictionary.

        Args:
            session_id: Unique session identifier.
            user_id: Owner user identifier.

        Returns:
            Dictionary with session row or None if not found.
        """
        return await self._driver.select_one_or_none(
            db_manager.get_sql("get-ai-session"), session_id=session_id, user_id=user_id
        )

    async def save_session(self, session_id: str, user_id: str, app_name: str, state: dict[str, object]) -> None:
        """Upsert session metadata and state JSON document.

        Args:
            session_id: Unique session identifier.
            user_id: Owner user identifier.
            app_name: Name of the hosting application.
            state: Serialized session state dictionary.
        """
        encoded_state = msgspec.json.encode(state).decode("utf-8")
        await self._driver.execute(
            db_manager.get_sql("upsert-ai-session"),
            session_id=session_id,
            user_id=user_id,
            app_name=app_name,
            state=encoded_state,
        )

    async def clear_session(self, session_id: str, user_id: str) -> None:
        """Delete session and associated history rows.

        Args:
            session_id: Unique session identifier.
            user_id: Owner user identifier.
        """
        await self._driver.execute(db_manager.get_sql("clear-ai-session"), session_id=session_id, user_id=user_id)


class OracleEventStore:
    """Oracle 26ai backed event log store."""

    def __init__(self, driver: OracleAsyncDriver) -> None:
        """Initialize event store with Oracle async driver.

        Args:
            driver: SQLSpec OracleAsyncDriver instance.
        """
        self._driver = driver

    async def append_event(self, event: AgentEvent) -> None:
        """Insert a monotonic event row into Oracle persistence.

        Args:
            event: AgentEvent instance to record.
        """
        encoded_content = msgspec.json.encode(event.content).decode("utf-8") if event.content else None
        encoded_actions = msgspec.json.encode(event.actions).decode("utf-8")
        await self._driver.execute(
            db_manager.get_sql("append-ai-event"),
            session_id=event.session_id,
            invocation_id=event.invocation_id,
            seq=event.seq,
            turn=event.turn,
            agent=event.agent,
            content=encoded_content,
            actions=encoded_actions,
        )

    async def list_events(self, session_id: str) -> list[AgentEvent]:
        """Fetch ordered history events for a given session.

        Args:
            session_id: Unique session identifier.

        Returns:
            Chronological list of AgentEvent instances.
        """
        rows = await self._driver.select(db_manager.get_sql("list-ai-events"), session_id=session_id)
        events: list[AgentEvent] = []
        for r in rows:
            content: Content | None = None
            if r.get("content"):
                raw_content = r["content"]
                if isinstance(raw_content, str):
                    content = msgspec.json.decode(raw_content.encode("utf-8"), type=Content)
                elif isinstance(raw_content, dict):
                    content = msgspec.convert(raw_content, type=Content)

            actions: dict[str, Any] = {}
            if r.get("actions"):
                raw_actions = r["actions"]
                if isinstance(raw_actions, str):
                    actions = msgspec.json.decode(raw_actions.encode("utf-8"), type=dict[str, Any])
                elif isinstance(raw_actions, dict):
                    actions = raw_actions

            events.append(
                AgentEvent(
                    session_id=str(r.get("session_id", "")),
                    invocation_id=str(r.get("invocation_id", "")),
                    agent=str(r.get("agent", "")),
                    content=content,
                    actions=actions,
                    seq=int(r.get("seq", 0)),
                    turn=int(r.get("turn", 0)),
                    partial=False,
                )
            )
        return events

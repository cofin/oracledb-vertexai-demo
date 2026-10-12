# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for OracleSessionStore, OracleEventStore, and ai-runtime.sql."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import db_manager
from app.domain.ai.runtime import AgentEvent, Content, OracleEventStore, OracleSessionStore, Part

pytestmark = pytest.mark.anyio


def test_ai_runtime_sql_targets_agent_session_and_agent_event() -> None:
    """Verify ai-runtime.sql targets agent_session/agent_event and migration 0002 exists."""
    migration_path = Path("src/app/db/migrations/0002_agent_runtime_and_hybrid_search.sql")
    assert migration_path.exists()
    migration_sql = migration_path.read_text(encoding="utf-8").lower()
    assert "create table agent_session" in migration_sql
    assert "create table agent_event" in migration_sql
    assert "on delete cascade" in migration_sql

    get_session_sql = str(db_manager.get_sql("get-ai-session")).lower()
    upsert_session_sql = str(db_manager.get_sql("upsert-ai-session")).lower()
    append_event_sql = str(db_manager.get_sql("append-ai-event")).lower()
    list_events_sql = str(db_manager.get_sql("list-ai-events")).lower()
    next_seq_sql = str(db_manager.get_sql("next-ai-event-seq")).lower()

    assert "agent_session" in get_session_sql
    assert "adk_session" not in get_session_sql
    assert "agent_session" in upsert_session_sql
    assert "agent_event" in append_event_sql
    assert "adk_event" not in append_event_sql
    assert "agent_event" in list_events_sql
    assert "coalesce(max(seq), 0) + 1" in next_seq_sql


async def test_oracle_session_store_commits_writes() -> None:
    """Verify OracleSessionStore calls commit() after save_session and clear_session."""
    mock_driver = MagicMock()
    mock_driver.execute = AsyncMock(return_value=None)
    mock_driver.commit = AsyncMock(return_value=None)

    store = OracleSessionStore(driver=mock_driver)
    await store.save_session("sess-1", "user-1", "cymbal_coffee", {"theme": "dark"})
    assert mock_driver.commit.await_count == 1

    await store.clear_session("sess-1", "user-1")
    assert mock_driver.commit.await_count == 2


async def test_oracle_event_store_commits_and_computes_next_seq() -> None:
    """Verify OracleEventStore commits append_event and computes next sequence number."""
    mock_driver = MagicMock()
    mock_driver.execute = AsyncMock(return_value=None)
    mock_driver.commit = AsyncMock(return_value=None)
    mock_driver.select_value_or_none = AsyncMock(return_value=4)

    store = OracleEventStore(driver=mock_driver)
    next_seq = await store.get_next_seq("sess-1")
    assert next_seq == 4

    event = AgentEvent(
        session_id="sess-1",
        invocation_id="inv-1",
        seq=next_seq,
        turn=2,
        agent="coffee_barista",
        content=Content(role="model", parts=[Part(text="Fresh pour-over ready.")]),
    )
    await store.append_event(event)
    assert mock_driver.commit.await_count == 1

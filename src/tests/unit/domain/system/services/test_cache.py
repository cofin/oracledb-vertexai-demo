# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for `CacheService`, `PersonaManager`, and `system.services` module contracts."""

from __future__ import annotations

import gc
import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.domain.system.schemas as system_schemas
import app.domain.system.services as system_services
from app.domain.system.schemas import CacheStatsRow, EmbeddingCache, ResponseCache
from app.domain.system.services import BASE_SYSTEM_INSTRUCTION, CacheService, PersonaManager
from app.lib.schema import FrozenBaseStruct
from app.lib.service import OracleLoaderService
from app.utils.serialization import decode_json

pytestmark = pytest.mark.anyio


async def test_system_services_module_boundaries_and_exports() -> None:
    """Verify `CacheService` inherits `OracleLoaderService` and `system.services` exports canonical public symbols."""
    assert issubclass(CacheService, OracleLoaderService)
    assert CacheService.__module__ == "app.domain.system.services._cache"
    assert PersonaManager.__module__ == "app.domain.system.services._personas"
    assert set(system_services.__all__) == {
        "BASE_SYSTEM_INSTRUCTION",
        "CacheService",
        "MetricsService",
        "PersonaManager",
    }


async def test_persona_manager_uses_frozen_persona_definition() -> None:
    """Verify `PersonaManager` resolves frozen `PersonaDefinition` entries and falls back to `barista`."""
    persona_cls = getattr(system_schemas, "PersonaDefinition", None)
    assert persona_cls is not None
    assert issubclass(persona_cls, FrozenBaseStruct)
    assert persona_cls.__module__ == "app.domain.system.schemas._persona"

    scientist = PersonaManager.PERSONAS["scientist"]
    assert isinstance(scientist, persona_cls)
    assert gc.is_tracked(scientist) is False
    assert PersonaManager.get_temperature("scientist") == 0.4
    assert PersonaManager.get_temperature("unknown-persona") == PersonaManager.PERSONAS["barista"].temperature

    prompt = PersonaManager.get_system_prompt("snob", BASE_SYSTEM_INSTRUCTION)
    assert BASE_SYSTEM_INSTRUCTION in prompt
    assert "## Persona Context: The Purist" in prompt


async def test_get_cached_response_is_single_typed_select(mock_driver) -> None:
    """Verify `CacheService.get_cached_response` executes a single typed select without committing."""
    cached = ResponseCache(
        id=1,
        cache_key="cache-key",
        response_data={"answer": "cached"},
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    mock_driver.select_one_or_none = AsyncMock(return_value=cached)
    mock_driver.execute = AsyncMock()
    mock_driver.commit = AsyncMock()

    result = await CacheService(mock_driver).get_cached_response("cache-key")

    assert result is cached
    assert mock_driver.select_one_or_none.await_args is not None
    _, kwargs = mock_driver.select_one_or_none.await_args
    assert kwargs["key"] == "cache-key"
    assert kwargs["schema_type"] is ResponseCache
    mock_driver.execute.assert_not_awaited()
    mock_driver.commit.assert_not_awaited()


async def test_set_cached_response_executes_single_atomic_merge(mock_driver) -> None:
    """Verify `CacheService.set_cached_response` executes `MERGE INTO response_cache` once and returns the row."""
    payload = {"answer": "Fresh pour-over", "from_cache": False}
    persisted = ResponseCache(
        id=5,
        cache_key="resp-key",
        response_data=payload,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=45),
    )
    mock_driver.select_value_or_none = AsyncMock()
    mock_driver.execute = AsyncMock()
    mock_driver.commit = AsyncMock()
    mock_driver.select_one_or_none = AsyncMock(return_value=persisted)

    result = await CacheService(mock_driver).set_cached_response("resp-key", payload, ttl_minutes=45)

    assert result is persisted
    mock_driver.select_value_or_none.assert_not_awaited()
    mock_driver.execute.assert_awaited_once()
    mock_driver.commit.assert_awaited_once()

    assert mock_driver.execute.await_args is not None
    exec_args, exec_kwargs = mock_driver.execute.await_args
    assert "MERGE INTO response_cache" in str(exec_args[0])
    assert exec_kwargs["cache_key"] == "resp-key"
    assert isinstance(exec_kwargs["response_data"], str)
    assert decode_json(exec_kwargs["response_data"]) == payload
    assert isinstance(exec_kwargs["expires_at"], datetime)


async def test_get_embedding_maps_full_row_to_typed_struct(mock_driver) -> None:
    """Verify `CacheService.get_embedding` maps the row to `EmbeddingCache` and increments hit count."""
    cached = EmbeddingCache(
        id=7,
        text_hash="abc",
        embedding=[0.1, 0.2, 0.3],
        model="gemini-embedding-2",
        created_at=datetime.now(UTC),
        last_accessed=datetime.now(UTC),
        hit_count=2,
    )
    mock_driver.select_one_or_none = AsyncMock(return_value=cached)
    mock_driver.execute = AsyncMock()
    mock_driver.commit = AsyncMock()

    result = await CacheService(mock_driver).get_embedding("dark roast", "gemini-embedding-2")

    assert result == [0.1, 0.2, 0.3]
    assert mock_driver.select_one_or_none.await_args is not None
    _, kwargs = mock_driver.select_one_or_none.await_args
    assert kwargs["schema_type"] is EmbeddingCache
    mock_driver.execute.assert_awaited_once()
    mock_driver.commit.assert_awaited_once()


async def test_get_embedding_returns_none_on_miss(mock_driver) -> None:
    """Verify `CacheService.get_embedding` returns `None` without executing an update on cache miss."""
    mock_driver.select_one_or_none = AsyncMock(return_value=None)
    mock_driver.execute = AsyncMock()
    mock_driver.commit = AsyncMock()

    result = await CacheService(mock_driver).get_embedding("dark roast", "gemini-embedding-2")

    assert result is None
    mock_driver.execute.assert_not_awaited()


async def test_save_embedding_executes_single_atomic_merge(mock_driver) -> None:
    """Verify `CacheService.save_embedding` executes `MERGE INTO embedding_cache` once without pre-selecting."""
    mock_driver.select_value_or_none = AsyncMock()
    mock_driver.execute = AsyncMock()
    mock_driver.commit = AsyncMock()
    vector = [0.25, 0.5, 0.75]

    await CacheService(mock_driver).save_embedding("ethiopian pour over", vector, "gemini-embedding-2")

    mock_driver.select_value_or_none.assert_not_awaited()
    mock_driver.execute.assert_awaited_once()
    mock_driver.commit.assert_awaited_once()

    assert mock_driver.execute.await_args is not None
    exec_args, exec_kwargs = mock_driver.execute.await_args
    assert "MERGE INTO embedding_cache" in str(exec_args[0])
    assert exec_kwargs["text_hash"] == hashlib.sha256(b"ethiopian pour over").hexdigest()
    assert exec_kwargs["embedding"] == vector
    assert exec_kwargs["model"] == "gemini-embedding-2"


async def test_delete_expired_responses_and_stale_sessions(mock_driver) -> None:
    """Verify `CacheService` cleanup methods delete expired responses and clamp session retention days."""
    mock_driver.execute = AsyncMock(side_effect=[MagicMock(rows_affected=3), MagicMock(rows_affected=2)])
    mock_driver.commit = AsyncMock()
    service = CacheService(mock_driver)

    deleted_responses = await service.delete_expired_responses()
    deleted_sessions = await service.delete_stale_agent_sessions(retention_days=0)

    assert deleted_responses == 3
    assert deleted_sessions == 2
    assert mock_driver.commit.await_count == 2
    _, session_kwargs = mock_driver.execute.await_args_list[1]
    assert session_kwargs["retention_days"] == 1


async def test_get_cache_stats_and_invalidate_cache(mock_driver) -> None:
    """Verify `CacheService.get_cache_stats` derives hit rate and `invalidate_cache` scopes table deletes."""
    mock_driver.select_one_or_none = AsyncMock(return_value=CacheStatsRow(total_hits=100, total_entries=12))
    mock_driver.execute = AsyncMock(side_effect=[MagicMock(rows_affected=4), MagicMock(rows_affected=6)])
    mock_driver.commit = AsyncMock()
    service = CacheService(mock_driver)

    stats = await service.get_cache_stats()
    deleted_all = await service.invalidate_cache()

    assert stats.total_hits == 100
    assert stats.total_entries == 12
    assert stats.cache_hit_rate == 50.0
    assert deleted_all == 10
    assert mock_driver.execute.await_count == 2
    mock_driver.commit.assert_awaited_once()

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Cache service contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.system.schemas import ResponseCache

pytestmark = pytest.mark.anyio


async def test_get_cached_response_is_single_typed_select(mock_driver) -> None:
    from app.domain.system.services.services import CacheService

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
    _, kwargs = mock_driver.select_one_or_none.await_args
    assert kwargs["key"] == "cache-key"
    assert kwargs["schema_type"] is ResponseCache
    mock_driver.execute.assert_not_awaited()
    mock_driver.commit.assert_not_awaited()


async def test_delete_expired_responses_is_explicit_cleanup_operation(mock_driver) -> None:
    from app.domain.system.services.services import CacheService

    execute_result = MagicMock(rows_affected=3)
    mock_driver.execute = AsyncMock(return_value=execute_result)
    mock_driver.commit = AsyncMock()

    deleted = await CacheService(mock_driver).delete_expired_responses()

    assert deleted == 3
    mock_driver.execute.assert_awaited_once()
    mock_driver.commit.assert_awaited_once()

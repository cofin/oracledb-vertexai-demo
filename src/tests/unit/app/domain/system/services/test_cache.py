# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Cache service contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.system.schemas import ResponseCache

pytestmark = pytest.mark.anyio


async def test_get_cached_response_is_single_typed_select() -> None:
    from app.domain.system.services.services import CacheService

    cached = ResponseCache(
        id=1,
        cache_key="cache-key",
        response_data={"answer": "cached"},
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    driver = MagicMock()
    driver.select_one_or_none = AsyncMock(return_value=cached)
    driver.execute = AsyncMock()
    driver.commit = AsyncMock()

    result = await CacheService(driver).get_cached_response("cache-key")

    assert result is cached
    _, kwargs = driver.select_one_or_none.await_args
    assert kwargs["key"] == "cache-key"
    assert kwargs["schema_type"] is ResponseCache
    driver.execute.assert_not_awaited()
    driver.commit.assert_not_awaited()


async def test_delete_expired_responses_is_explicit_cleanup_operation() -> None:
    from app.domain.system.services.services import CacheService

    execute_result = MagicMock(rows_affected=3)
    driver = MagicMock()
    driver.execute = AsyncMock(return_value=execute_result)
    driver.commit = AsyncMock()

    deleted = await CacheService(driver).delete_expired_responses()

    assert deleted == 3
    driver.execute.assert_awaited_once()
    driver.commit.assert_awaited_once()

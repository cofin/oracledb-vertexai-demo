# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from app.domain.system.controllers import MetricsController
from app.domain.system.schemas import PerformanceStats


class FakeMetricsService:
    async def get_performance_stats(self, hours: int) -> PerformanceStats:
        assert hours == 24
        return PerformanceStats(
            total_searches=12,
            avg_search_time_ms=45.5,
            avg_oracle_time_ms=8.1,
            avg_similarity_score=0.91,
        )


class FailingMetricsService:
    async def get_performance_stats(self, hours: int) -> PerformanceStats:
        del hours
        msg = "metrics unavailable"
        raise ValueError(msg)


@pytest.mark.anyio
async def test_get_metrics_returns_normalized_payload() -> None:
    result = await MetricsController.get_metrics.fn(
        object.__new__(MetricsController), metrics_service=FakeMetricsService()
    )

    assert result.total_searches == 12
    assert result.avg_search_time_ms == 45.5
    assert result.avg_oracle_time_ms == 8.1
    assert result.avg_similarity_score == 0.91


@pytest.mark.anyio
async def test_get_metrics_returns_zero_fallback_on_service_error() -> None:
    result = await MetricsController.get_metrics.fn(
        object.__new__(MetricsController), metrics_service=FailingMetricsService()
    )

    assert result.total_searches == 0
    assert result.avg_search_time_ms == 0
    assert result.avg_oracle_time_ms == 0
    assert result.avg_similarity_score == 0

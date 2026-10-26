# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``GET /api/metrics/summary`` returns ``MetricsSummary(cards=[...])`` comparing disjoint 1h windows."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.domain.system.controllers import MetricsController
from app.domain.system.schemas import CacheStats, PerformanceStats


class FakeMetricsService:
    """Captures requested `(hours, window_end_hours)` windows and returns deterministic stats."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    async def get_performance_stats(self, hours: int = 24, *, window_end_hours: int = 0) -> PerformanceStats:
        self.calls.append((hours, window_end_hours))
        if (hours, window_end_hours) == (2, 1):
            return PerformanceStats(
                total_searches=21, avg_search_time_ms=80.0, avg_oracle_time_ms=14.0, avg_similarity_score=0.89
            )
        return PerformanceStats(
            total_searches=42, avg_search_time_ms=73.0, avg_oracle_time_ms=12.0, avg_similarity_score=0.91
        )


class FakeCacheService:
    """Returns deterministic embedding cache stats for summary card tests."""

    async def get_cache_stats(self) -> CacheStats:
        return CacheStats(total_hits=875, total_entries=10, cache_hit_rate=87.5)


@pytest.mark.anyio
async def test_get_metrics_summary_returns_cards_array_over_disjoint_windows() -> None:
    """Verify `MetricsController.get_metrics_summary` compares `(0, 1h]` against disjoint `(1h, 2h]`."""
    metrics_service = FakeMetricsService()
    result = await MetricsController.get_metrics_summary.fn(
        MetricsController(owner=MagicMock()), metrics_service=metrics_service, cache_service=FakeCacheService()
    )

    assert metrics_service.calls == [(1, 0), (2, 1)]
    assert hasattr(result, "cards")
    assert len(result.cards) == 4
    assert [card.label for card in result.cards] == [
        "Total Searches",
        "Avg Response Time",
        "Oracle Vector Time",
        "Cache Hit Rate",
    ]
    assert result.cards[0].trend == "up"
    assert result.cards[0].trend_value == "100.0%"

# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``GET /api/metrics/summary`` returns ``MetricsSummary(cards=[...])`` so the page can iterate via ``<template ls-for>``."""

from __future__ import annotations

import pytest

from app.domain.system.controllers import MetricsController
from app.domain.system.schemas import CacheStats, PerformanceStats


class FakeMetricsService:
    async def get_performance_stats(self, hours: int) -> PerformanceStats:
        del hours
        return PerformanceStats(
            total_searches=42,
            avg_search_time_ms=73.0,
            avg_oracle_time_ms=12.0,
            avg_similarity_score=0.91,
        )


class FakeCacheService:
    async def get_cache_stats(self) -> CacheStats:
        return CacheStats(total_hits=875, total_entries=10, cache_hit_rate=87.5)


@pytest.mark.anyio
async def test_get_metrics_summary_returns_cards_array() -> None:
    result = await MetricsController.get_metrics_summary.fn(
        object.__new__(MetricsController),
        metrics_service=FakeMetricsService(),
        cache_service=FakeCacheService(),
    )

    assert hasattr(result, "cards")
    assert len(result.cards) == 4
    assert [card.label for card in result.cards] == [
        "Total Searches",
        "Avg Response Time",
        "Oracle Vector Time",
        "Cache Hit Rate",
    ]

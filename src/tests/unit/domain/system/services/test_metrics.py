# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for `MetricsService`, disjoint window binds, and frozen `system.schemas` models."""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from sqlspec.driver._async import AsyncDriverAdapterBase

import app.domain.system.schemas as system_schemas
from app.domain.system.schemas import (
    CacheStats,
    CacheStatsRow,
    EmbeddingCache,
    MetricCard,
    MetricsBreakdown,
    MetricsBreakdownRow,
    MetricsCharts,
    MetricsScatterPoint,
    MetricsSummary,
    MetricsTimeSeries,
    MetricsTimeSeriesPoints,
    MetricsTimeSeriesRow,
    PerformanceStats,
    ResponseCache,
    SearchMetricsCreate,
)
from app.domain.system.services import MetricsService
from app.lib.schema import FrozenBaseStruct
from app.lib.service import OracleLoaderService


class RecordingDriver(AsyncDriverAdapterBase):
    """Captures SQLSpec execute calls for service-boundary assertions."""

    def __init__(self) -> None:
        self.executed: list[Any] = []
        self.committed = False

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        del args, kwargs
        self.executed.append(statement)
        return None

    async def commit(self) -> None:
        self.committed = True


def _sample_schema_instances() -> list[FrozenBaseStruct]:
    """Construct representative instances of every schema exported by `app.domain.system.schemas`."""
    now = datetime.now(UTC)
    points = MetricsTimeSeriesPoints(total_ms=[10.0], oracle_ms=[4.0], embedding_ms=[5.0])
    time_series = MetricsTimeSeries(labels=["12:00"], series=points)
    scatter = MetricsScatterPoint(similarity_score=0.92, total_ms=10.0, oracle_ms=4.0, embedding_ms=5.0)
    breakdown = MetricsBreakdown(labels=["Oracle Vector Search"], values=[4.0])
    card = MetricCard(label="Total Searches", value="42", trend="up", trend_value="10.0%")
    instances: list[Any] = [
        CacheStats(total_hits=10, total_entries=2, cache_hit_rate=9.1),
        CacheStatsRow(total_hits=10, total_entries=2),
        EmbeddingCache(
            id=1, text_hash="h", embedding=[0.1], model="gemini-embedding-2", created_at=now, last_accessed=now
        ),
        card,
        breakdown,
        MetricsBreakdownRow(embedding_ms=5.0, oracle_ms=4.0, ai_ms=1.0, intent_ms=0.5, other_ms=0.2),
        MetricsCharts(time_series=time_series, scatter=[scatter], breakdown=breakdown),
        scatter,
        MetricsSummary(cards=[card]),
        time_series,
        points,
        MetricsTimeSeriesRow(bucket="12:00", total_ms=10.0, oracle_ms=4.0, embedding_ms=5.0),
        PerformanceStats(total_searches=5, avg_search_time_ms=12.0, avg_oracle_time_ms=4.0, avg_similarity_score=0.9),
        ResponseCache(id=1, cache_key="k", response_data={"ok": True}, created_at=now),
        SearchMetricsCreate(
            query_id="q1", search_time_ms=10.0, embedding_time_ms=5.0, oracle_time_ms=4.0, result_count=3
        ),
    ]
    persona_cls = getattr(system_schemas, "PersonaDefinition", None)
    assert persona_cls is not None, "PersonaDefinition must be exported from app.domain.system.schemas"
    instances.append(
        persona_cls(
            name="The Friendly Barista",
            description="Warm, efficient, and ready to help.",
            language_style="Friendly",
            focus_areas=["all drinks"],
            system_prompt_addon="Recommend popular drinks.",
        )
    )
    return instances


def test_metrics_service_inherits_oracle_loader_service() -> None:
    """Verify `MetricsService` inherits from `OracleLoaderService` in `app.domain.system.services._metrics`."""
    assert issubclass(MetricsService, OracleLoaderService)
    assert MetricsService.__module__ == "app.domain.system.services._metrics"


def test_all_system_schemas_are_frozen_and_gc_exempt() -> None:
    """Verify every schema exported by `app.domain.system.schemas` inherits `FrozenBaseStruct` and omits GC tracking."""
    exported_types = [getattr(system_schemas, name) for name in system_schemas.__all__]
    assert len(exported_types) == 16
    for schema_cls in exported_types:
        assert issubclass(schema_cls, FrozenBaseStruct), f"{schema_cls.__name__} must inherit FrozenBaseStruct"
        assert schema_cls.__struct_config__.frozen is True
        assert schema_cls.__struct_config__.gc is False

    instances = _sample_schema_instances()
    assert len(instances) == len(exported_types)
    for instance in instances:
        assert gc.is_tracked(instance) is False


@pytest.mark.anyio
async def test_record_search_uses_database_column_names() -> None:
    """Verify `MetricsService.record_search` uses snake_case database column names and commits."""
    driver = RecordingDriver()  # type: ignore[abstract]
    service = MetricsService(cast("Any", driver))

    await service.record_search(
        SearchMetricsCreate(
            query_id="query-1",
            user_id="demo",
            search_time_ms=12.5,
            embedding_time_ms=3.0,
            oracle_time_ms=4.0,
            similarity_score=0.91,
            result_count=2,
        )
    )

    assert driver.executed, "record_search must execute one insert"
    assert driver.committed is True
    statement = str(driver.executed[0])
    assert "result_count" in statement
    assert "resultCount" not in statement


@pytest.mark.anyio
async def test_get_performance_stats_binds_disjoint_hour_window(mock_driver) -> None:
    """Verify `MetricsService.get_performance_stats` binds `window_start_hours` and `window_end_hours`."""
    expected = PerformanceStats(
        total_searches=18, avg_search_time_ms=34.0, avg_oracle_time_ms=9.0, avg_similarity_score=0.88
    )
    mock_driver.select_one_or_none = AsyncMock(side_effect=[expected, None])
    service = MetricsService(mock_driver)

    prior_window = await service.get_performance_stats(hours=2, window_end_hours=1)
    empty_window = await service.get_performance_stats(hours=1)

    assert prior_window == expected
    assert empty_window == PerformanceStats(
        total_searches=0, avg_search_time_ms=0.0, avg_oracle_time_ms=0.0, avg_similarity_score=0.0
    )

    first_args, first_kwargs = mock_driver.select_one_or_none.await_args_list[0]
    assert ":window_start_hours" in str(first_args[0])
    assert first_kwargs == {"window_start_hours": 2, "window_end_hours": 1, "schema_type": PerformanceStats}

    _, second_kwargs = mock_driver.select_one_or_none.await_args_list[1]
    assert second_kwargs == {"window_start_hours": 1, "window_end_hours": 0, "schema_type": PerformanceStats}


@pytest.mark.anyio
async def test_get_chart_data_projects_time_series_scatter_and_breakdown(mock_driver) -> None:
    """Verify `MetricsService.get_chart_data` aggregates time-series, scatter points, and fallback breakdown rows."""
    mock_driver.select = AsyncMock(
        side_effect=[
            [MetricsTimeSeriesRow(bucket="14:05", total_ms=28.0, oracle_ms=7.0, embedding_ms=15.0)],
            [MetricsScatterPoint(similarity_score=0.93, total_ms=28.0, oracle_ms=7.0, embedding_ms=15.0)],
        ]
    )
    mock_driver.select_one_or_none = AsyncMock(return_value=None)

    charts = await MetricsService(mock_driver).get_chart_data(hours=1)

    assert charts.time_series.labels == ["14:05"]
    assert charts.time_series.series.oracle_ms == [7.0]
    assert len(charts.scatter) == 1
    assert charts.breakdown.values == [0.0, 0.0, 0.0, 0.0, 0.0]

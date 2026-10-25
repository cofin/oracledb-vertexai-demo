# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""System performance and cache telemetry schemas."""

from app.lib.schema import CamelizedFrozenStruct

__all__ = (
    "CacheStats",
    "CacheStatsRow",
    "MetricCard",
    "MetricsBreakdown",
    "MetricsBreakdownRow",
    "MetricsCharts",
    "MetricsScatterPoint",
    "MetricsSummary",
    "MetricsTimeSeries",
    "MetricsTimeSeriesPoints",
    "MetricsTimeSeriesRow",
    "PerformanceStats",
    "SearchMetricsCreate",
)


class SearchMetricsCreate(CamelizedFrozenStruct, frozen=True, kw_only=True):
    """Row inserted into ``search_metric``."""

    query_id: str
    user_id: str | None = None
    search_time_ms: float
    embedding_time_ms: float
    oracle_time_ms: float
    ai_time_ms: float = 0.0
    intent_time_ms: float = 0.0
    similarity_score: float | None = None
    result_count: int


class PerformanceStats(CamelizedFrozenStruct, frozen=True):
    """Aggregate latency and volume across a window of ``search_metric`` rows."""

    total_searches: int
    avg_search_time_ms: float
    avg_oracle_time_ms: float
    avg_similarity_score: float


class CacheStatsRow(CamelizedFrozenStruct, frozen=True):
    """Single-row projection from ``get-cache-stats``."""

    total_hits: int
    total_entries: int


class CacheStats(CamelizedFrozenStruct, frozen=True):
    """Embedding-cache hit/usage rollup with derived hit rate."""

    total_hits: int
    total_entries: int
    cache_hit_rate: float


class MetricCard(CamelizedFrozenStruct, frozen=True):
    """Single card on the metrics summary panel."""

    label: str
    value: str | float
    trend: str = "neutral"
    trend_value: str | float | None = None


class MetricsSummary(CamelizedFrozenStruct, frozen=True):
    """Card list rendered client-side in the Explore dashboard."""

    cards: list[MetricCard]


class MetricsTimeSeriesPoints(CamelizedFrozenStruct, frozen=True):
    """Per-stage latency series for the latency chart."""

    total_ms: list[float]
    oracle_ms: list[float]
    embedding_ms: list[float]


class MetricsTimeSeriesRow(CamelizedFrozenStruct, frozen=True):
    """Single per-minute bucket projected from ``metrics-time-series``."""

    bucket: str
    total_ms: float
    oracle_ms: float
    embedding_ms: float


class MetricsTimeSeries(CamelizedFrozenStruct, frozen=True):
    """Latency series payload consumed by ApexCharts."""

    labels: list[str]
    series: MetricsTimeSeriesPoints


class MetricsScatterPoint(CamelizedFrozenStruct, frozen=True):
    """Single vector-search point for similarity-vs-latency charts."""

    similarity_score: float
    total_ms: float
    oracle_ms: float
    embedding_ms: float


class MetricsBreakdownRow(CamelizedFrozenStruct, frozen=True):
    """Aggregate component timing row projected from ``search_metric``."""

    embedding_ms: float
    oracle_ms: float
    ai_ms: float
    intent_ms: float
    other_ms: float


class MetricsBreakdown(CamelizedFrozenStruct, frozen=True):
    """Labels and values for the system breakdown chart."""

    labels: list[str]
    values: list[float]


class MetricsCharts(CamelizedFrozenStruct, frozen=True):
    """Complete Explore dashboard chart payload."""

    time_series: MetricsTimeSeries
    scatter: list[MetricsScatterPoint]
    breakdown: MetricsBreakdown

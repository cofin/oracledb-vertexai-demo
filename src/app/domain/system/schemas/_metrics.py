# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from app.lib.schema import CamelizedBaseStruct


class SearchMetricsCreate(CamelizedBaseStruct, omit_defaults=True, kw_only=True):
    """Search-metrics row to persist."""

    query_id: str
    user_id: str | None = None
    search_time_ms: float
    embedding_time_ms: float
    oracle_time_ms: float
    ai_time_ms: float = 0.0
    intent_time_ms: float = 0.0
    similarity_score: float | None = None
    result_count: int


class PerformanceStats(CamelizedBaseStruct, omit_defaults=True):
    """Aggregate latency / volume stats for a window of search_metric rows."""

    total_searches: int
    avg_search_time_ms: float
    avg_oracle_time_ms: float
    avg_similarity_score: float


class CacheStatsRow(CamelizedBaseStruct, omit_defaults=True):
    """Single-row projection of ``get-cache-stats`` (hit_count + entry counts)."""

    total_hits: int
    total_entries: int


class CacheStats(CamelizedBaseStruct, omit_defaults=True):
    """Embedding-cache hit/usage rollup with derived hit-rate."""

    total_hits: int
    total_entries: int
    cache_hit_rate: float


class MetricsDashboard(CamelizedBaseStruct, omit_defaults=True):
    """Legacy ``GET /metrics`` payload retained for the operations dashboard."""

    total_searches: int
    avg_search_time_ms: float
    avg_oracle_time_ms: float
    avg_similarity_score: float


class MetricCard(CamelizedBaseStruct, omit_defaults=True):
    """Metric card data for dashboard."""

    label: str
    value: str | float
    trend: str = "neutral"  # up, down, neutral
    trend_value: str | float | None = None


class MetricsSummary(CamelizedBaseStruct, omit_defaults=True):
    """Aggregated metric cards for the explore-page summary panel.

    The shape is ``{cards: [MetricCard, ...]}`` so the page can iterate
    client-side via ``<template ls-for="card in $data.cards">``.
    """

    cards: list[MetricCard]


class MetricsTimeSeriesPoints(CamelizedBaseStruct, omit_defaults=True):
    """Per-stage latency tracks for the explore-page latency chart (Panel 4)."""

    total_ms: list[float]
    oracle_ms: list[float]
    embedding_ms: list[float]


class MetricsTimeSeriesRow(CamelizedBaseStruct, omit_defaults=True):
    """Single per-minute bucket from the ``metrics-time-series`` SQL."""

    bucket: str
    total_ms: float
    oracle_ms: float
    embedding_ms: float


class MetricsTimeSeries(CamelizedBaseStruct, omit_defaults=True):
    """Time-series payload consumed by the Alpine + ApexCharts panel."""

    labels: list[str]
    series: MetricsTimeSeriesPoints


class ClassifyCompareIntent(CamelizedBaseStruct, omit_defaults=True):
    """Per-intent slice of the Ch 3 ``classify --compare`` artifact."""

    intent: str
    gold: int
    legacy: int
    new: int
    precision: float
    recall: float
    agreement: float


class ClassifyCompare(CamelizedBaseStruct, omit_defaults=True):
    """Explore-page Panel 5 payload — gold vs legacy vs new across intents."""

    intents: list[ClassifyCompareIntent]

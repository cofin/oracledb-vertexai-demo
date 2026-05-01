# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

from app.lib.schema import CamelizedBaseStruct


class SearchMetricsCreate(CamelizedBaseStruct, omit_defaults=True, kw_only=True):
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


class PerformanceStats(CamelizedBaseStruct, omit_defaults=True):
    """Aggregate latency and volume across a window of ``search_metric`` rows."""

    total_searches: int
    avg_search_time_ms: float
    avg_oracle_time_ms: float
    avg_similarity_score: float


class CacheStatsRow(CamelizedBaseStruct, omit_defaults=True):
    """Single-row projection from ``get-cache-stats``."""

    total_hits: int
    total_entries: int


class CacheStats(CamelizedBaseStruct, omit_defaults=True):
    """Embedding-cache hit/usage rollup with derived hit rate."""

    total_hits: int
    total_entries: int
    cache_hit_rate: float


class MetricCard(CamelizedBaseStruct, omit_defaults=True):
    """Single card on the metrics summary panel."""

    label: str
    value: str | float
    trend: str = "neutral"
    trend_value: str | float | None = None


class MetricsSummary(CamelizedBaseStruct, omit_defaults=True):
    """Card list rendered client-side via ``<template ls-for>``."""

    cards: list[MetricCard]


class MetricsTimeSeriesPoints(CamelizedBaseStruct, omit_defaults=True):
    """Per-stage latency series for the latency chart."""

    total_ms: list[float]
    oracle_ms: list[float]
    embedding_ms: list[float]


class MetricsTimeSeriesRow(CamelizedBaseStruct, omit_defaults=True):
    """Single per-minute bucket projected from ``metrics-time-series``."""

    bucket: str
    total_ms: float
    oracle_ms: float
    embedding_ms: float


class MetricsTimeSeries(CamelizedBaseStruct, omit_defaults=True):
    """Latency series payload consumed by ApexCharts."""

    labels: list[str]
    series: MetricsTimeSeriesPoints


class ClassifyCompare(CamelizedBaseStruct, omit_defaults=True):
    """Offline intent-classifier comparison payload for the explore page."""

    available: bool
    rows: list[dict[str, Any]]
    summary: dict[str, Any]
    hint: str | None = None

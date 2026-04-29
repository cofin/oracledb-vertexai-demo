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

from typing import Any

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


class MetricCard(CamelizedBaseStruct, omit_defaults=True):
    """Metric card data for dashboard."""

    label: str
    value: str | float
    trend: str = "neutral"  # up, down, neutral
    trend_value: str | float | None = None


class MetricsSummary(CamelizedBaseStruct, omit_defaults=True):
    """Aggregated metric cards for the dashboard summary panel."""

    total_searches: MetricCard
    avg_response_time: MetricCard
    avg_oracle_time: MetricCard
    cache_hit_rate: MetricCard


class TimeSeries(CamelizedBaseStruct, omit_defaults=True):
    """Latency time-series points across the dashboard window."""

    labels: list[str]
    total_latency: list[float]
    oracle_latency: list[float]
    vertex_latency: list[float]


class ChartData(CamelizedBaseStruct, omit_defaults=True):
    """Combined chart payload for the dashboard."""

    time_series: TimeSeries
    scatter_data: list[dict[str, float]]
    breakdown_data: dict[str, Any]

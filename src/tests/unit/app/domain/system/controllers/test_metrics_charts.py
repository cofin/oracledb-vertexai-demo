# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``GET /api/metrics/charts`` returns the dashboard chart payload."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.domain.system.controllers import MetricsController
from app.domain.system.schemas import (
    MetricsBreakdown,
    MetricsCharts,
    MetricsScatterPoint,
    MetricsTimeSeries,
    MetricsTimeSeriesPoints,
)


class FakeMetricsService:
    """Returns deterministic chart data so controller wiring can be asserted."""

    async def get_chart_data(self, hours: int) -> MetricsCharts:
        assert hours == 1, "Panel 4 charts the most recent hour"
        return MetricsCharts(
            time_series=MetricsTimeSeries(
                labels=["00:01", "00:02", "00:03"],
                series=MetricsTimeSeriesPoints(
                    total_ms=[40.0, 55.0, 30.0],
                    oracle_ms=[10.0, 15.0, 8.0],
                    embedding_ms=[25.0, 35.0, 18.0],
                ),
            ),
            scatter=[
                MetricsScatterPoint(similarity_score=0.91, total_ms=40.0, oracle_ms=10.0, embedding_ms=25.0)
            ],
            breakdown=MetricsBreakdown(
                labels=["Vertex AI Embedding", "Oracle Vector Search", "Application Logic"],
                values=[25.0, 10.0, 5.0],
            ),
        )


@pytest.mark.anyio
async def test_get_chart_data_returns_dashboard_charts() -> None:
    result = await MetricsController.get_chart_data.fn(
        MetricsController(owner=MagicMock()), metrics_service=FakeMetricsService()
    )

    assert result.time_series.labels == ["00:01", "00:02", "00:03"]
    assert result.time_series.series.total_ms == [40.0, 55.0, 30.0]
    assert result.scatter[0].similarity_score == 0.91
    assert result.breakdown.labels == ["Vertex AI Embedding", "Oracle Vector Search", "Application Logic"]

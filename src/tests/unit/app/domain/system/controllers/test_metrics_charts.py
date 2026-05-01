# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``GET /api/metrics/charts`` returns ``MetricsTimeSeries`` (labels + series substruct)."""

from __future__ import annotations

import pytest

from app.domain.system.controllers import MetricsController
from app.domain.system.schemas import MetricsTimeSeries, MetricsTimeSeriesPoints


class FakeMetricsService:
    """Returns a deterministic ``MetricsTimeSeries`` so the wiring can be asserted."""

    async def get_time_series(self, hours: int) -> MetricsTimeSeries:
        assert hours == 1, "Panel 4 charts the most recent hour"
        return MetricsTimeSeries(
            labels=["00:01", "00:02", "00:03"],
            series=MetricsTimeSeriesPoints(
                total_ms=[40.0, 55.0, 30.0],
                oracle_ms=[10.0, 15.0, 8.0],
                embedding_ms=[25.0, 35.0, 18.0],
            ),
        )


@pytest.mark.anyio
async def test_get_chart_data_returns_labels_and_series() -> None:
    result = await MetricsController.get_chart_data.fn(
        object.__new__(MetricsController), metrics_service=FakeMetricsService()
    )

    assert result.labels == ["00:01", "00:02", "00:03"]
    assert result.series.total_ms == [40.0, 55.0, 30.0]
    assert result.series.oracle_ms == [10.0, 15.0, 8.0]
    assert result.series.embedding_ms == [25.0, 35.0, 18.0]

from __future__ import annotations

import pytest

from app.domain.system.controllers._metrics import MetricsController


class FakeMetricsService:
    async def get_performance_stats(self, hours: int) -> dict[str, float]:
        assert hours == 24
        return {
            "total_searches": 12,
            "avg_search_time_ms": 45.5,
            "avg_oracle_time_ms": 8.1,
            "avg_similarity_score": 0.91,
        }


class FailingMetricsService:
    async def get_performance_stats(self, hours: int) -> dict[str, float]:
        msg = "metrics unavailable"
        raise ValueError(msg)


@pytest.mark.anyio
async def test_get_metrics_returns_normalized_payload() -> None:
    controller = object.__new__(MetricsController)
    result = await MetricsController.get_metrics.fn(  # type: ignore[arg-type]
        controller, metrics_service=FakeMetricsService()
    )

    assert result == {
        "total_searches": 12,
        "avg_search_time_ms": 45.5,
        "avg_oracle_time_ms": 8.1,
        "avg_similarity_score": 0.91,
    }


@pytest.mark.anyio
async def test_get_metrics_returns_zero_fallback_on_service_error() -> None:
    controller = object.__new__(MetricsController)
    result = await MetricsController.get_metrics.fn(  # type: ignore[arg-type]
        controller, metrics_service=FailingMetricsService()
    )

    assert result == {
        "total_searches": 0,
        "avg_search_time_ms": 0,
        "avg_oracle_time_ms": 0,
        "avg_similarity_score": 0,
    }

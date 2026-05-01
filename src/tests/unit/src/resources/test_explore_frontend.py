# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Explore dashboard frontend contracts."""

from __future__ import annotations

from tests.support.paths import APP_ROOT


EXPLORE_TEMPLATE = APP_ROOT / "domain" / "web" / "templates" / "pages" / "explore.html.j2"


def test_explore_dashboard_defines_bounded_apexcharts() -> None:
    template = EXPLORE_TEMPLATE.read_text()

    assert "function dashboardCharts()" in template
    assert 'data-chart-host="response-trends"' in template
    assert 'data-chart-host="vector-performance"' in template
    assert 'data-chart-host="system-breakdown"' in template
    assert "type: 'line'" in template
    assert "type: 'scatter'" in template
    assert "type: 'donut'" in template
    assert "height: 286" in template

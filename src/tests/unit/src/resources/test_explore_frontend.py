# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Explore dashboard frontend contracts."""

from __future__ import annotations

from tests.support.paths import APP_ROOT

EXPLORE_TEMPLATE = APP_ROOT / "domain" / "web" / "templates" / "pages" / "explore.html.j2"


def test_explore_dashboard_defines_bounded_apexcharts() -> None:
    template = EXPLORE_TEMPLATE.read_text()

    assert "function metricsSummary()" in template
    assert "function renderEmptyChart" in template
    assert "function dashboardCharts()" in template
    assert 'x-data="metricsSummary()"' in template
    assert 'data-chart-host="response-trends"' in template
    assert 'data-chart-host="vector-performance"' in template
    assert 'data-chart-host="system-breakdown"' in template
    assert "type: 'line'" in template
    assert "type: 'scatter'" in template
    assert "barHeight: '58%'" in template
    assert "No response metrics yet" in template
    assert "No component metrics yet" in template
    assert "height: 286" in template
    assert "data-plan-line" in template
    assert "text-surface" in template
    assert "classifyComparePanel" not in template
    assert "classify-compare" not in template


def test_explore_htmx_bootstrap_processes_existing_dom() -> None:
    source = (APP_ROOT.parent / "resources" / "main.js").read_text()

    assert "htmx.process(document.body)" in source

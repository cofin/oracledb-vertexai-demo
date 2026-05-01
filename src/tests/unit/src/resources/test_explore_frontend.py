# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Explore dashboard frontend contracts."""

from __future__ import annotations

from tests.support.paths import APP_ROOT

EXPLORE_TEMPLATE = APP_ROOT / "domain" / "web" / "templates" / "pages" / "explore.html.j2"
PLAN_PARTIAL = APP_ROOT / "domain" / "web" / "templates" / "partials" / "plan_lines.html.j2"


def test_explore_dashboard_defines_bounded_apexcharts() -> None:
    template = EXPLORE_TEMPLATE.read_text()
    plan_partial = PLAN_PARTIAL.read_text()
    source = (APP_ROOT.parent / "resources" / "main.js").read_text()

    assert "const renderEmptyChart" in source
    assert "const initDashboardCharts" in source
    assert "new ApexCharts" in source
    assert 'hx-get="/api/metrics/summary"' in template
    assert 'hx-swap="json"' in template
    assert 'ls-for="card in cards"' in template
    assert "card.trend === 'up'" in template
    assert "data-dashboard-charts" in template
    assert 'data-chart-host="response-trends"' in template
    assert 'data-chart-host="vector-performance"' in template
    assert 'data-chart-host="system-breakdown"' in template
    assert 'type: "line"' in source
    assert 'type: "scatter"' in source
    assert 'barHeight: "58%"' in source
    assert "No response metrics yet" in source
    assert "No component metrics yet" in source
    assert "height: 286" in source
    assert "data-plan-line" in plan_partial
    assert "data-plan-row" in plan_partial
    assert "text-surface" in template
    assert "x-data" not in template
    assert "x-ref" not in template
    assert "Search results and SQL plan update from the same query." in template
    assert "Search for a drink, roast, flavor, or breakfast item" in template
    assert 'hx-get="/api/explain-plan"' not in template
    assert "classifyComparePanel" not in template
    assert "classify-compare" not in template


def test_explore_htmx_bootstrap_processes_existing_dom() -> None:
    source = (APP_ROOT.parent / "resources" / "main.js").read_text()

    assert "htmx.process(document.body)" in source

# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Explore dashboard frontend contracts."""

from __future__ import annotations

from tests.support.paths import APP_ROOT

EXPLORE_TEMPLATE = APP_ROOT / "domain" / "web" / "templates" / "pages" / "explore.html.j2"
PLAN_PARTIAL = APP_ROOT / "domain" / "web" / "templates" / "partials" / "plan_lines.html.j2"
VECTOR_CALCULATOR_SCRIPT = APP_ROOT.parent / "resources" / "vector-calculator.js"


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
    assert "overflow-x-auto" not in plan_partial
    assert "min-w-[42rem]" not in plan_partial
    assert "table-fixed" in plan_partial
    assert "break-words" in plan_partial
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


def test_explore_vector_calculator_panel_contract() -> None:
    template = EXPLORE_TEMPLATE.read_text()
    panel_start = template.index('id="panel-vector-calculator"')
    panel_end = template.index("</section>", panel_start) + len("</section>")
    panel = template[panel_start:panel_end]

    assert 'data-ui-panel="vector-calculator"' in panel
    assert "Vector storage calculator" in panel
    assert "data-vector-calculator" in panel
    assert 'data-vector-input="rowCount"' in panel
    assert 'data-vector-input="dimensions"' in panel
    assert 'data-vector-input="format"' in panel
    assert 'data-vector-input="indexType"' in panel
    assert 'data-vector-input="hnswM"' in panel
    assert 'data-preset-dimensions="3072"' in panel
    assert 'data-preset-format="FLOAT32"' in panel
    assert 'data-output="rawSize"' in panel
    assert 'data-output="indexSize"' in panel
    assert 'data-output="totalSize"' in panel
    assert 'data-output="vectorMemory"' in panel
    assert 'data-output="mediaComparison"' in panel
    assert "hx-" not in panel
    assert "x-data" not in panel


def test_vector_calculator_client_logic_contract() -> None:
    source = VECTOR_CALCULATOR_SCRIPT.read_text()
    main_source = (APP_ROOT.parent / "resources" / "main.js").read_text()

    assert 'import { initVectorCalculator } from "./vector-calculator.js"' in main_source
    assert "void initVectorCalculator()" in main_source
    assert "fetch(" not in source
    assert "rowCount * dimensions * 4" in source
    assert "Math.ceil(dimensions / 8)" in source
    assert "rowCount * hnswM * dimensions * 4" in source
    assert "formatBytes" in source
    assert "mediaComparisonFor" in source
    assert "Vector memory" in source

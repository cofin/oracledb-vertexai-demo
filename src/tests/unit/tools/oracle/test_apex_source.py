# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Contract tests for the source-controlled APEX Operations Console."""

from __future__ import annotations

from src.tests.support.paths import SRC_ROOT

APP_ROOT = SRC_ROOT / "apex" / "cymbal-coffee-ops"


def test_apex_operations_console_uses_sqlcl_26_project_layout() -> None:
    """The checked-in APEXlang app follows the SQLcl-generated source layout."""
    assert (APP_ROOT / ".apex" / "apexlang.json").is_file()
    assert (APP_ROOT / "application.apx").is_file()
    assert (APP_ROOT / "deployments" / "default.json").is_file()
    assert (APP_ROOT / "shared-components" / "lists.apx").is_file()
    assert (APP_ROOT / "supporting-objects" / "supporting-objects.apx").is_file()


def test_apex_operations_console_pages_and_navigation_cover_demo_workflows() -> None:
    """The app source exposes the operations-console pages called for by the spec."""
    expected_pages = {
        "p00001-home.apx": "Dashboard",
        "p00002-products.apx": "Product Catalog",
        "p00003-stores.apx": "Stores",
        "p00004-store-inventory.apx": "Store Inventory",
        "p00005-availability.apx": "Availability Lookup",
        "p00006-vector-recommendations.apx": "Vector Recommendations",
        "p00007-integration-health.apx": "Integration Health",
    }

    for filename, title in expected_pages.items():
        page_text = (APP_ROOT / "pages" / filename).read_text()
        assert f"title: {title}" in page_text

    navigation = (APP_ROOT / "shared-components" / "lists.apx").read_text()
    for title in expected_pages.values():
        assert f"label: {title}" in navigation


def test_apex_operations_console_makes_litestar_api_bridge_visible() -> None:
    """Static source content documents the filtered /api/apex bridge used by APEX."""
    source_text = "\n".join(path.read_text() for path in (APP_ROOT / "pages").glob("*.apx"))
    application_text = (APP_ROOT / "application.apx").read_text()

    expected_endpoints = {
        "/api/apex/products",
        "/api/apex/stores",
        "/api/apex/inventory/summary",
        "/api/apex/products/{product_id}/availability",
        "/api/apex/recommendations",
        "/api/apex/vector/status",
        "/api/apex/openapi/status",
    }

    for endpoint in expected_endpoints:
        assert endpoint in source_text or endpoint in application_text

    assert "/api/apex/openapi/status" in source_text
    assert "/api/apex/vector/status" in source_text


def test_apex_operations_console_reports_use_real_oracle_data_sources() -> None:
    """Operations reports are backed by SQL over the seeded Oracle demo tables."""
    expected_page_sources = {
        "p00002-products.apx": "from product",
        "p00003-stores.apx": "from store",
        "p00004-store-inventory.apx": "store_product_inventory",
        "p00007-integration-health.apx": "from product",
    }

    for filename, sql_fragment in expected_page_sources.items():
        page_text = (APP_ROOT / "pages" / filename).read_text()
        assert "type: interactiveReport" in page_text
        assert "location: localDatabase" in page_text
        assert "type: sqlQuery" in page_text
        assert "sqlQuery:" in page_text
        assert sql_fragment in page_text

    integration_text = (APP_ROOT / "pages" / "p00007-integration-health.apx").read_text()
    assert "gemini-embedding-2" in integration_text

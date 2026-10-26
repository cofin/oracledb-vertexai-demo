# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit and offline SQLcl APEXlang compiler tests for `src/apex/cymbal-coffee-ops/`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from tools.oracle.apex_lang import ApexLang, ApexLangConfig
from tools.oracle.sqlcl_installer import SQLclInstaller

APEX_ROOT = Path("src/apex")
APP_DIR = APEX_ROOT / "cymbal-coffee-ops"
PAGES_DIR = APP_DIR / "pages"
REGION_HEADER_RE = re.compile(r"^\s*region\s+([A-Za-z0-9_-]+)\s*\(", re.MULTILINE)


def _extract_region_blocks(apx_text: str) -> list[tuple[str, str]]:
    """Extract `(region_identifier, block_body)` pairs from an APEXlang `.apx` page file."""
    regions: list[tuple[str, str]] = []
    for match in REGION_HEADER_RE.finditer(apx_text):
        region_id = match.group(1)
        open_paren_idx = match.end() - 1
        depth = 0
        end_idx = len(apx_text)
        for idx in range(open_paren_idx, len(apx_text)):
            char = apx_text[idx]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end_idx = idx + 1
                    break
        regions.append((region_id, apx_text[open_paren_idx:end_idx]))
    return regions


def test_application_targets_apex_26_1_and_omits_rest_server_fk_hazards() -> None:
    """Verify `application.apx` sets `compatibilityMode: 26.1` and `.apx` files omit `restDataSourceServer`."""
    app_text = (APP_DIR / "application.apx").read_text(encoding="utf-8")
    assert "compatibilityMode: 26.1" in app_text
    assert "compatibilityMode: 24.2" not in app_text
    assert "Cymbal Coffee" in app_text

    apx_files = sorted(APP_DIR.rglob("*.apx"))
    assert apx_files
    for apx_file in apx_files:
        text = apx_file.read_text(encoding="utf-8")
        assert "restDataSourceServer" not in text, f"Unexpected restDataSourceServer in {apx_file}"


@pytest.mark.parametrize(
    "page_filename",
    [
        "p00001-home.apx",
        "p00002-products.apx",
        "p00003-stores.apx",
        "p00004-store-inventory.apx",
        "p00005-availability.apx",
        "p00006-vector-recommendations.apx",
        "p00007-integration-health.apx",
    ],
)
def test_operational_pages_contain_zero_empty_static_content_stub_regions(page_filename: str) -> None:
    """Verify every `staticContent` region across Pages 1-7 has populated `htmlCode` or item children."""
    page_path = PAGES_DIR / page_filename
    text = page_path.read_text(encoding="utf-8")
    regions = _extract_region_blocks(text)
    assert regions, f"Expected at least one region in {page_filename}"

    for region_id, block in regions:
        if "type: staticContent" not in block:
            continue
        has_html_source = "htmlCode:" in block
        has_child_items = f"region: @{region_id}" in text
        assert has_html_source or has_child_items, (
            f"Empty staticContent stub region @{region_id} in {page_filename} lacks htmlCode or child items"
        )


def test_page_1_home_queries_live_catalog_store_inventory_and_annotation_kpis() -> None:
    """Verify Page 1 queries `product`, `store`, `store_product_inventory`, and `user_annotations_usage`."""
    lowered = (PAGES_DIR / "p00001-home.apx").read_text(encoding="utf-8").lower()
    for required_table in ("product", "store", "store_product_inventory", "user_annotations_usage"):
        assert required_table in lowered


def test_page_2_and_4_and_5_query_catalog_vector_readiness_and_store_availability_precedence() -> None:
    """Verify Page 2 reports vector readiness and Pages 4-5 apply store-level inventory precedence over `product.in_stock`."""
    page2 = (PAGES_DIR / "p00002-products.apx").read_text(encoding="utf-8").lower()
    assert "from product" in page2
    assert "embedding is not null" in page2

    page4 = (PAGES_DIR / "p00004-store-inventory.apx").read_text(encoding="utf-8").lower()
    assert "store_product_inventory" in page4

    page5 = (PAGES_DIR / "p00005-availability.apx").read_text(encoding="utf-8").lower()
    assert "store_product_inventory" in page5
    assert "pickup_available" in page5 or "stock_status" in page5
    assert "p.in_stock" in page5


def test_page_3_stores_builds_keyless_google_maps_urls_without_browser_geolocation() -> None:
    """Verify Page 3 renders keyless Google Maps search URLs from seeded store addresses without browser coordinates."""
    page3 = (PAGES_DIR / "p00003-stores.apx").read_text(encoding="utf-8")
    lowered = page3.lower()
    assert "https://www.google.com/maps/search/?api=1&query=" in page3
    assert "from store" in lowered
    for forbidden_token in ("navigator.geolocation", "user_lat", "user_lng", "browser_lat", "radius_miles"):
        assert forbidden_token not in lowered


def test_page_6_concierge_invokes_apex_ai_generate_with_coffee_vertex_ai_and_product_grounding() -> None:
    """Verify Page 6 wires `P6_PROMPT`, `P6_CATEGORY`, and `APEX_AI.GENERATE` targeting `COFFEE_VERTEX_AI`."""
    page6 = (PAGES_DIR / "p00006-vector-recommendations.apx").read_text(encoding="utf-8")
    upper = page6.upper()
    assert "P6_PROMPT" in upper
    assert "P6_CATEGORY" in upper
    assert "APEX_AI.GENERATE" in upper
    assert "COFFEE_VERTEX_AI" in upper
    assert "FROM PRODUCT" in upper


def test_page_7_health_inspects_annotations_apex_release_credentials_and_vector_coverage() -> None:
    """Verify Page 7 inspects `user_annotations_usage`, `apex_release`, credentials, and 3072-dim vector coverage."""
    lowered = (PAGES_DIR / "p00007-integration-health.apx").read_text(encoding="utf-8").lower()
    assert "user_annotations_usage" in lowered
    assert "apex_release" in lowered
    assert "apex_workspace_credentials" in lowered
    assert "3072" in lowered
    assert "embedding is not null" in lowered


def test_apex_readme_documents_direct_vertex_ai_gateway_and_sqlcl_workflow() -> None:
    """Verify `src/apex/README.md` documents Direct Vertex AI, Litestar Gateway mode, and SQLcl 26.1.2 commands."""
    readme = (APEX_ROOT / "README.md").read_text(encoding="utf-8")
    assert "configure-vertex" in readme
    assert "--mode direct" in readme
    assert "--mode gateway" in readme
    assert "COFFEE_VERTEX_AI" in readme
    assert "infra apex validate" in readme
    assert "infra apex import" in readme


def test_sqlcl_offline_apex_validate_compiles_cymbal_coffee_ops_cleanly() -> None:
    """Run offline SQLcl 26.1.2+ `apex validate` on `src/apex/cymbal-coffee-ops` when SQLcl is installed."""
    installer = SQLclInstaller()
    status = installer.apexlang_status()
    if not status.capable:
        pytest.skip(status.message)

    apex_lang = ApexLang(installer=installer, config=ApexLangConfig(src_root=APEX_ROOT))
    result = apex_lang.validate(alias="cymbal-coffee-ops")
    combined_output = f"{result.stdout}\n{result.stderr}"
    assert "APEXLang Compile Errors:" not in combined_output

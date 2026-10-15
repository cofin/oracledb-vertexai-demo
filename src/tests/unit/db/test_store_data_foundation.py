# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Verify baseline migration DDL, Oracle 26ai schema annotations, and committed fixture integrity."""

from __future__ import annotations

import gzip
import json
from typing import Any

from app.db.utils import COFFEE_SHOP_TABLES
from tests.support.paths import APP_ROOT

FIXTURES_DIR = APP_ROOT / "db" / "fixtures"
MIGRATIONS_DIR = APP_ROOT / "db" / "migrations"


def _read_fixture(name: str) -> list[dict[str, Any]]:
    """Read and parse a gzipped JSON fixture array by table name."""
    with gzip.open(FIXTURES_DIR / f"{name}.json.gz", "rt", encoding="utf-8") as fixture:
        data = json.load(fixture)
    assert isinstance(data, list)
    return data


def test_store_data_foundation_stays_in_baseline_migration() -> None:
    """Verify the squashed `0001` baseline migration contains store coordinates and inventory DDL."""
    migration_files = sorted(path.name for path in MIGRATIONS_DIR.glob("*.sql"))

    assert migration_files == ["0001_cymball_coffee_products.sql"]

    migration = (MIGRATIONS_DIR / "0001_cymball_coffee_products.sql").read_text(encoding="utf-8")
    assert "latitude NUMBER(9, 6)" in migration
    assert "longitude NUMBER(9, 6)" in migration
    assert "CREATE TABLE store_product_inventory" in migration
    assert "CONSTRAINT store_product_inventory_uk UNIQUE (store_id, product_id)" in migration


def test_baseline_migration_uses_inline_schema_annotations() -> None:
    """Verify `0001` declares inline Oracle 26ai `ANNOTATIONS (...)` on tables, columns, and indexes."""
    migration = (MIGRATIONS_DIR / "0001_cymball_coffee_products.sql").read_text(encoding="utf-8")

    assert "embedding VECTOR(3072, FLOAT32)\n        ANNOTATIONS (" in migration
    assert ") INMEMORY PRIORITY HIGH\nANNOTATIONS (" in migration
    assert ")\nANNOTATIONS (\n    Display 'Cymbal Coffee stores'" in migration
    assert "stock_status VARCHAR2(20) NOT NULL\n        ANNOTATIONS (" in migration
    assert "CREATE TABLE embedding_cache" in migration
    assert "Embedding_Model 'gemini-embedding-2'" in migration
    assert "Embedding_Purpose 'document'" in migration
    assert "CREATE INDEX product_in_stock_idx ON product (in_stock)\nANNOTATIONS (" in migration
    assert "ALTER TABLE product ANNOTATIONS" not in migration


def test_fixture_table_order_loads_inventory_after_parents() -> None:
    """Verify `COFFEE_SHOP_TABLES` orders `store` and `product` before `store_product_inventory`."""
    assert COFFEE_SHOP_TABLES[:3] == ["store", "product", "store_product_inventory"]
    assert "chat_route" in COFFEE_SHOP_TABLES


def test_inventory_fixture_uses_single_gzipped_load_artifact() -> None:
    """Verify `store_product_inventory.json.gz` is the sole inventory fixture artifact."""
    assert (FIXTURES_DIR / "store_product_inventory.json.gz").is_file()
    assert not (FIXTURES_DIR / "store_product_inventory.json").exists()


def test_store_fixtures_include_coordinates_timezone_and_dallas() -> None:
    """Verify `store.json.gz` includes Dallas Arts District and required store metadata."""
    stores = _read_fixture("store")

    assert any(
        store["name"] == "Cymbal Coffee Dallas Arts District"
        and store["city"] == "Dallas"
        and store["state"] == "TX"
        and store["zip"] == "75201"
        for store in stores
    )
    for store in stores:
        assert isinstance(store.get("latitude"), float)
        assert isinstance(store.get("longitude"), float)
        assert store.get("timezone")
        assert store.get("address")
        assert store.get("phone")
        assert store.get("hours")
        assert store.get("metadata")


def test_product_fixtures_use_explicit_stock_booleans() -> None:
    """Verify `product.json.gz` uses boolean `in_stock` values."""
    products = _read_fixture("product")

    assert products
    assert all(isinstance(product.get("in_stock"), bool) for product in products)


def test_store_product_inventory_fixture_is_curated_and_consistent() -> None:
    """Verify `store_product_inventory.json.gz` references valid store/product IDs without duplicates."""
    stores = {store["id"] for store in _read_fixture("store")}
    products = {product["id"] for product in _read_fixture("product")}
    inventory = _read_fixture("store_product_inventory")

    assert inventory
    assert len(inventory) < len(stores) * len(products)
    assert {item["stock_status"] for item in inventory} == {"IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"}
    assert {16, 13, 4, 1}.issubset({item["store_id"] for item in inventory})

    seen_pairs: set[tuple[int, int]] = set()
    for item in inventory:
        pair = (item["store_id"], item["product_id"])
        assert pair not in seen_pairs
        seen_pairs.add(pair)
        assert item["store_id"] in stores
        assert item["product_id"] in products
        assert isinstance(item["quantity_available"], int)
        assert item["quantity_available"] >= 0
        assert isinstance(item["pickup_available"], bool)

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Script to generate realistic inventory fixtures for Cymbal Coffee."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any, cast

PRODUCTS_PER_STORE = 100
MAX_QUANTITY = 50
LOW_STOCK_THRESHOLD = 10
OUT_OF_STOCK_PRODUCT_ID = 231


def generate_inventory(output_file: Path | None = None) -> None:
    """Generate inventory data based on existing store and product fixtures.

    This function reads the store and product fixtures, generates deterministic
    inventory records for a subset of products in each store, and saves the result
    to a gzipped JSON file.
    """
    root_dir = Path(__file__).resolve().parents[2]
    fixtures_dir = root_dir / "src" / "app" / "db" / "fixtures"

    if output_file is None:
        output_file = fixtures_dir / "store_product_inventory.json.gz"

    stores = load_fixture(fixtures_dir / "store.json.gz")
    products = load_fixture(fixtures_dir / "product.json.gz")
    inventory = build_inventory_rows(stores, products)
    write_inventory(output_file, inventory)


def load_fixture(fixture_file: Path) -> list[dict[str, Any]]:
    """Load one gzipped JSON fixture file."""
    with gzip.open(fixture_file, "rb") as f:
        return cast("list[dict[str, Any]]", json.load(f))


def build_inventory_rows(stores: list[dict[str, Any]], products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build deterministic store/product inventory rows."""
    inventory: list[dict[str, Any]] = []
    current_id = 1

    for store_index, store in enumerate(stores):
        store_id = store["id"]
        for product in selected_products(products, store_index):
            inventory.append(inventory_row(current_id, store_id, product["id"]))
            current_id += 1
    return inventory


def selected_products(products: list[dict[str, Any]], store_index: int) -> list[dict[str, Any]]:
    """Return a deterministic rotating product subset for one store."""
    if not products:
        return []
    product_count = min(PRODUCTS_PER_STORE, len(products))
    start = store_index * product_count
    return [products[(start + offset) % len(products)] for offset in range(product_count)]


def inventory_row(current_id: int, store_id: int, product_id: int) -> dict[str, Any]:
    """Build one deterministic inventory fixture row."""
    if product_id == OUT_OF_STOCK_PRODUCT_ID:
        return {
            "id": current_id,
            "store_id": store_id,
            "product_id": product_id,
            "quantity_available": 0,
            "stock_status": "OUT_OF_STOCK",
            "pickup_available": False,
        }

    quantity = (store_id * 17 + product_id * 13 + current_id) % (MAX_QUANTITY + 1)
    return {
        "id": current_id,
        "store_id": store_id,
        "product_id": product_id,
        "quantity_available": quantity,
        "stock_status": stock_status(quantity),
        "pickup_available": (store_id + product_id + current_id) % 2 == 0,
    }


def stock_status(quantity: int) -> str:
    """Map fixture quantity to the inventory status enum."""
    if quantity == 0:
        return "OUT_OF_STOCK"
    if quantity < LOW_STOCK_THRESHOLD:
        return "LOW_STOCK"
    return "IN_STOCK"


def write_inventory(output_file: Path, inventory: list[dict[str, Any]]) -> None:
    """Write inventory rows as JSON or gzipped JSON."""
    if output_file.suffix == ".gz":
        with gzip.open(output_file, "wt", encoding="utf-8") as f:
            json.dump(inventory, f, indent=2)
    else:
        with Path(output_file).open("w", encoding="utf-8") as f:
            json.dump(inventory, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate inventory fixtures.")
    parser.add_argument("--output", type=str, help="Path to output file")
    args = parser.parse_args()

    out_path = Path(args.output) if args.output else None
    generate_inventory(output_file=out_path)

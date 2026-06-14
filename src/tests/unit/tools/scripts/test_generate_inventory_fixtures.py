# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the inventory fixture generator script."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from tools.scripts.generate_inventory_fixtures import generate_inventory


def test_generate_inventory_writes_gzipped_load_fixture_name(tmp_path: Path) -> None:
    output_file = tmp_path / "store_product_inventory.json.gz"

    generate_inventory(output_file=output_file)

    assert output_file.is_file()

    with gzip.open(output_file, "rt", encoding="utf-8") as fixture:
        data = json.load(fixture)

    assert isinstance(data, list)
    assert data

    for item in data:
        assert "store_id" in item
        assert "product_id" in item
        assert "quantity_available" in item
        assert "stock_status" in item
        assert "pickup_available" in item

        assert isinstance(item["store_id"], int)
        assert isinstance(item["product_id"], int)
        assert isinstance(item["quantity_available"], int)
        assert item["stock_status"] in {"IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"}
        assert isinstance(item["pickup_available"], bool)

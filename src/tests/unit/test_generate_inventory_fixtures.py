# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for generate_inventory_fixtures script."""

import gzip
import json
from pathlib import Path

from tools.scripts.generate_inventory_fixtures import generate_inventory


def test_generate_inventory(tmp_path: Path) -> None:
    """Test that generate_inventory creates a valid fixture file."""
    output_file = tmp_path / "test_inventory.json.gz"
    generate_inventory(output_file=output_file)

    assert output_file.exists()

    with gzip.open(output_file, "rb") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) > 0

    for item in data:
        assert "store_id" in item
        assert "product_id" in item
        assert "quantity_available" in item
        assert "stock_status" in item
        assert "pickup_available" in item

        assert isinstance(item["store_id"], int)
        assert isinstance(item["product_id"], int)
        assert isinstance(item["quantity_available"], int)
        assert item["stock_status"] in ["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"]
        assert isinstance(item["pickup_available"], bool)

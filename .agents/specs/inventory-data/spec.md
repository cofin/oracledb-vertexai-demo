# Flow: inventory-data

## Specification
The current inventory fixtures in `src/app/db/fixtures/store_product_inventory.json.gz` are sparse and only cover a few stores (1, 4, 13, 16). To make the inventory features meaningful in the demo, we need to populate realistic inventory data for all stores and a representative set of products.

### Requirements
*   Generate inventory data for all stores listed in `store.json.gz`.
*   Assign a representative subset of products (from `product.json.gz`) to each store.
*   Vary the quantities and stock status (`IN_STOCK`, `LOW_STOCK`, `OUT_OF_STOCK`) to provide realistic search results.
*   Ensure the output matches the schema of the `store_product_inventory` table:
    *   `id`: Sequential integer starting from 1 (required for SQLSpec FixtureLoader MERGE join)
    *   `store_id`: Valid ID from `store.json.gz`
    *   `product_id`: Valid ID from `product.json.gz`
    *   `quantity_available`: Integer >= 0
    *   `stock_status`: One of 'IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK'
    *   `pickup_available`: Boolean (true/false)

### Code Analysis Summary
*   Fixtures are located in `src/app/db/fixtures/`.
*   We use the gzipped load artifact `store_product_inventory.json.gz` so `coffee upgrade` and `coffee load-fixtures --tables store_product_inventory` load the intended table fixture without a shadowing plain JSON copy.
*   `src/app/db/utils.py` defines the loading order: `store`, `product`, `store_product_inventory`.
*   `FixtureLoader` handles reading and upserting the data, joining on `id`.

## Implementation Plan

### Phase 1: Data Generation Script
- [x] 1.1 Create a Python script at `tools/scripts/generate_inventory_fixtures.py` to generate full inventory fixtures.
- [x] 1.2 The script must read `store.json.gz` and `product.json.gz` to get valid IDs.
- [x] 1.3 Generate non-trivial inventory rows for all stores, including sequential `id` values.
- [x] 1.4 Save the output to `src/app/db/fixtures/store_product_inventory.json.gz`.
- [x] 1.5 Create a unit test at `src/tests/unit/tools/scripts/test_generate_inventory_fixtures.py` to validate generated data structure.

### Phase 2: Verification
- [x] 2.1 Run the generator script to update the fixture file in `/tmp` and write it to the workspace.
- [x] 2.2 Run `UV_CACHE_DIR=/tmp/uv_cache uv run coffee load-fixtures --tables store_product_inventory` to load the new data.
- [x] 2.3 Verify that the database contains the expected number of rows using a simple SQL query.

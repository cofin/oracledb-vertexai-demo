# Flow: Store Query Services (store-query-services_20260501)

*Chapter 2 of [store-location-inventory-chat_20260501](../store-location-inventory-chat_20260501/prd.md)*
*Beads: `oracledb-vertexai-f6u.2`*

---

## Objective

Expose grounded store, hours, nearest-store, maps URL, and inventory query primitives through the existing service and ADK tool-service boundaries.

---

## Dependencies

- Requires `store-data-foundation_20260501`.
- Must preserve the named-SQL pattern from the domain-service restructure chapter.

---

## Scope

### Store Service

Add or extend methods in `src/app/domain/products/services/services.py`:

- `get_store_hours(store_id)`
- `search_stores_by_zip(zip_code)`
- `find_nearest_stores(latitude, longitude, limit=5)`
- `find_stores_by_location(city=None, state=None, zip_code=None)`

For the demo dataset, nearest-store sorting may load candidate stores through named SQL and rank with a Python Haversine helper. Do not call Google geocoding, Places, Distance Matrix, or Routes APIs.

### Inventory Service

Add service methods:

- `get_store_inventory(store_id)`
- `find_stores_with_product(product_id, latitude=None, longitude=None)`
- `find_product_availability(query, location_hint=None, coordinates=None)`

The implementation may keep inventory methods on `StoreService` initially if that matches the existing domain shape, but the contract must stay schema-owned and testable.

### ADK Tool Service

Extend `AgentToolsService` with closure-bound tools:

- `find_stores_by_location(city=None, state=None, zip_code=None)`
- `get_store_hours(store_id)`
- `find_nearest_stores(latitude, longitude)`
- `find_stores_with_product(product_query, latitude=None, longitude=None)`

Keep tools deterministic and backed by service results.

### Maps URLs

Add app-code URL builders for:

- store search URL
- directions URL without browser origin
- directions URL with browser origin

Use structured URL construction and escaping.

---

## Tests

- Unit tests for city, state, zip, id, hours, and nearest-store service behavior.
- Unit tests for inventory lookup by store and product.
- Unit tests for Maps URL construction and escaping.
- Existing `test_adk.py` tool-factory expectations updated for the expanded tool set.
- SQL registry tests updated for `inventory.sql` and widened `stores.sql`.

---

## Acceptance Criteria

- No inline SQL is introduced.
- Store lookups and inventory lookups return typed schemas or schema-shaped dicts consistent with current service patterns.
- Nearest ranking uses seeded local coordinates only.
- Maps URLs work without a Google Maps API key.
- SQL telemetry can identify named store/inventory SQL phases without raw browser coordinates.

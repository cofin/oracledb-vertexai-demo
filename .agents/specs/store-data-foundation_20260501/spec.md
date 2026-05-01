# Flow: Store Data Foundation (store-data-foundation_20260501)

*Chapter 1 of [store-location-inventory-chat_20260501](../store-location-inventory-chat_20260501/prd.md)*
*Beads: TBD*

---

## Objective

Make the local dataset capable of answering store-location, nearest-store, directions, and store-level product availability questions.

This branch will drop and recreate the demo database. Do not create a timestamped forward migration. Modify only `src/app/db/migrations/0001_cymball_coffee_products.sql` for schema changes.

---

## Scope

### Schema

- Add store location fields to the `store` table:
  - `latitude NUMBER(9,6)`
  - `longitude NUMBER(9,6)`
  - `timezone VARCHAR2(64)`
  - `google_place_id VARCHAR2(255)`
- Add `store_product_inventory` to `0001_cymball_coffee_products.sql`:
  - `id`
  - `store_id`
  - `product_id`
  - `quantity_available`
  - `stock_status`
  - `pickup_available`
  - `updated_at`
  - unique `(store_id, product_id)`
  - indexes for `store_id`, `product_id`, `stock_status`, and `(product_id, stock_status)`
- Add baseline comments for store coordinates and inventory status semantics.

### Fixtures

- Update all existing store fixtures with lat/lng/timezone and optional `google_place_id`.
- Add `Cymbal Coffee Dallas Arts District`:
  - city/state/zip: `Dallas`, `TX`, `75201`
  - timezone: `America/Chicago`
  - approximate coordinates: `32.7876`, `-96.7994`
  - metadata: wifi, seating, meeting rooms, early hours, local art
- Make product `in_stock` fixture values explicit booleans.
- Add `src/app/db/fixtures/store_product_inventory.json.gz`.
- Seed a curated inventory subset, not all 122 products x every store.
- Include deterministic inventory for Dallas, Seattle, Berkeley, and at least one "near me" scenario.

### Schemas and Loader

- Update `Store` and related product schemas in `src/app/domain/products/schemas/_products.py`.
- Add store-inventory schemas in the existing product/domain schema module unless implementation research shows a clearer local pattern.
- Update fixture load ordering so inventory loads after stores and products.

---

## Implementation Plan

1. Update the `0001` baseline only.
2. Update product/store schemas.
3. Update and regenerate compressed fixtures.
4. Add or update fixture loader table ordering.
5. Add named SQL coverage for inventory query keys needed by later chapters.
6. Drop and recreate the DB, run the baseline migration, and load fixtures.

---

## Tests

- Unit tests for fixture loading order and inventory fixture shape.
- Unit tests that product `in_stock` fixture values are explicit.
- Integration or database smoke that the Dallas store loads and can be selected by city, state, and zip.
- Integration or database smoke that `store_product_inventory` enforces FK and unique constraints.

---

## Acceptance Criteria

- No migration files are added beyond editing `0001_cymball_coffee_products.sql`.
- All existing stores plus Dallas have coordinates, timezone, hours, address, phone, and metadata.
- Dallas can be found by city, state, zip, and nearest-store ranking inputs.
- Inventory fixtures include `IN_STOCK`, `LOW_STOCK`, and `OUT_OF_STOCK`.
- Fixture load succeeds after a fresh drop/recreate.
- No chat behavior changes are required in this chapter.

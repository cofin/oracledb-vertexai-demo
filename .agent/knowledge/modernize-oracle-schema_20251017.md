# Knowledge Entry: modernize-oracle-schema_20251017

- **Flow ID:** `modernize-oracle-schema_20251017`
- **Description:** Align Oracle schema with modern data model parity and update downstream service/fixture behavior
- **Completed:** 2026-02-26
- **Archived:** 2026-02-26
- **Topics:** oracle, schema, sqlspec, fixtures, testing

## Summary
This flow validated that the Oracle schema and application-layer assumptions are aligned for store-aware, vector-enabled behavior. It also updated developer-facing documentation so schema expectations are explicit and current.

## Patterns Elevated
- Keep migration README updated with concrete baseline tables and type usage after schema modernization.

## Key Files
- `app/db/migrations/0001_cymball_coffee_products.sql`
- `app/db/utils.py`
- `app/domain/products/services/_product.py`
- `app/db/migrations/README.md`
- `README.md`

## Learnings (verbatim)

- Modern Oracle baseline is already captured in `0001_cymball_coffee_products.sql` with `BOOLEAN`, `JSON`, and `VECTOR` columns plus `store` table parity.
- Fixture load ordering should include `store` before dependent semantic tables to keep imports deterministic.
- Product reads should normalize Oracle boolean nullability (`NVL(in_stock, TRUE)`) for stable typed API responses.

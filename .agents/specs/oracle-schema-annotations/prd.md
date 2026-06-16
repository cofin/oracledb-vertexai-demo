# Master PRD: Oracle Schema Annotations

*PRD ID: `oracle-schema-annotations`*
*Created: 2026-06-13*
*Status: In Progress*

---

## North Star

Show Oracle AI Database 26ai schema annotations as part of the Cymbal Coffee
reference schema, not as an isolated toy example. The baseline DDL should
declare database-resident metadata for the product, store, inventory, cache,
metric, vector-column, and supported-index objects so developers can inspect
application intent directly from Oracle data dictionary views.

This is a schema/documentation feature only. The app does not need to consume
annotations at runtime in this PRD.

---

## External Research

Oracle 26ai supports `ANNOTATIONS(...)` on supported schema objects at creation
time and through `ALTER` statements. Annotation names have optional freeform
values, are additive, and are exposed through dictionary views such as
`USER_ANNOTATIONS_USAGE`, `ALL_ANNOTATIONS_USAGE`, and
`DBA_ANNOTATIONS_USAGE`.

Official docs reviewed:

- Oracle SQL Language Reference 26ai, `annotations_clause`:
  <https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/annotations_clause.html>
- Oracle Database Development Guide, "Registering Application Data Usage with
  the Database":
  <https://docs.oracle.com/en/database/oracle/oracle-database/26/adfns/registering-application-data-usage-database.html>
- Oracle Database Reference 26ai, `ALL_ANNOTATIONS_USAGE` and
  `USER_ANNOTATIONS_USAGE`:
  <https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/ALL_ANNOTATIONS_USAGE.html>
  <https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/USER_ANNOTATIONS_USAGE.html>
- Oracle All Things SQL blog, comment-to-annotation migration guidance:
  <https://blogs.oracle.com/sql/how-to-convert-object-comments-to-schema-annotations>

Key conclusions:

- `CREATE TABLE`, `ALTER TABLE`, `CREATE VIEW`, `ALTER VIEW`,
  `CREATE MATERIALIZED VIEW`, `ALTER MATERIALIZED VIEW`, `CREATE INDEX`, and
  `ALTER INDEX` are documented annotation surfaces.
- Table and column annotations fit this app best because the baseline schema
  already documents its intent with `COMMENT ON TABLE` and `COMMENT ON COLUMN`.
- Normal index annotations are useful where the SQL Language Reference
  documents `CREATE INDEX ... ANNOTATIONS(...)`. The current
  `CREATE VECTOR INDEX` page does not document an annotations clause, so vector
  metadata should be demonstrated on the vector columns unless runtime evidence
  proves a supported vector-index placement.
- Existing comments should stay for compatibility with tools that read
  `USER_TAB_COMMENTS` / `USER_COL_COMMENTS`; annotations should be added as the
  richer 26ai demonstration surface.

---

## Codebase Findings

### Current DDL Surface

`src/app/db/migrations/0001_cymball_coffee_products.sql` owns the baseline
schema. It already contains comments for:

- `product`, `store`, `store_product_inventory`, `response_cache`,
  `embedding_cache`, and `search_metric` tables.
- Vector and inventory/privacy columns such as `product.embedding`,
  `product.in_stock`, `store.latitude`, `store.longitude`,
  `store.google_place_id`, `store_product_inventory.stock_status`, and
  `embedding_cache.embedding`.
- HNSW vector indexes for `product.embedding` and `embedding_cache.embedding`.

This PRD should modify the baseline migration, not add a later migration, since
the branch is still curating the reference demo schema and fixture foundation.

### SQLSpec Migration Behavior

The project pins `sqlspec[adk,mypyc,oracledb,performance]==0.50.0`.
Local verification against the installed package showed:

- `sqlglot.parse_one(..., read="oracle")` does not fully model inline
  annotation syntax yet.
- `SQLFileLoader.add_named_sql()` preserves Oracle annotation DDL as raw SQL.
- SQLSpec's migration loader returns `sql_obj.raw_sql`.
- The migration runner executes SQL migrations through
  `driver.execute_script(sql_statement)`.

Therefore parser support is not a design blocker and must not force less
idiomatic DDL. The baseline migration should use correct Oracle inline
annotation syntax in the existing `CREATE` statements where Oracle supports it.
The implementation still must run a real Oracle 26ai migration smoke test
because the database is the source of truth for this DDL.

---

## Product Decisions

1. **Demonstrate annotations inline in the existing baseline DDL.**
   Update `src/app/db/migrations/0001_cymball_coffee_products.sql` directly.
   Add `ANNOTATIONS(...)` clauses to the existing `CREATE TABLE` statements,
   column definitions, and supported index definitions. Do not create a new
   migration and do not use separate `ALTER ... ANNOTATIONS(...)` statements as
   the primary implementation.

2. **Keep existing `COMMENT ON` statements.**
   Comments are familiar and tool-compatible. Annotations demonstrate richer
   metadata without breaking older introspection flows.

3. **Use a small, consistent annotation vocabulary.**
   Prefer readable names such as `Display`, `Description`, `AI_Surface`,
   `Embedding_Model`, `Embedding_Dimensions`, `Privacy`, `Data_Role`,
   `Cache_Role`, `Distance`, and `Target_Accuracy`. Use quoted identifiers only
   when Oracle reserved words or spaces require them.

4. **Annotate the demo-critical objects first.**
   Focus on product/search, store/location/privacy, inventory grounding, caches,
   metrics, vector columns, and ordinary B-tree indexes where the index
   metadata teaches something. Do not annotate every timestamp or ordinary
   index.

5. **Document queryable metadata.**
   Add docs that show how to query `USER_ANNOTATIONS_USAGE` so readers can see
   the metadata Oracle stores.

---

## Roadmap

### Chapter 1 - `schema-annotations-ddl`

Add Oracle 26ai schema annotations to the baseline DDL and verify Oracle exposes
them after migration.

Deliverables:

- Update `src/app/db/migrations/0001_cymball_coffee_products.sql`.
- Add inline table annotations to the existing `CREATE TABLE` DDL for
  `product`, `store`, `store_product_inventory`, `response_cache`,
  `embedding_cache`, and `search_metric`.
- Add inline column annotations to the existing column definitions for the
  vector, inventory, location, privacy, cache, and metric columns that carry
  demo semantics.
- Add inline annotations to supported normal index DDL such as
  `product_in_stock_idx`, `store_location_idx`, and
  `store_product_inventory_status_idx`.
- Keep existing `COMMENT ON` statements unless a comment has become factually
  stale.
- Verify annotations through `USER_ANNOTATIONS_USAGE` after applying
  migrations on Oracle 26ai.

### Chapter 2 - `schema-annotations-docs`

Update public docs and maintainer guidance so annotations are part of the demo
story.

Deliverables:

- Update `src/app/db/migrations/README.md` with a concise schema annotations
  section and an introspection query.
- Update `docs/reference/internals.md` to explain why the demo keeps comments
  and annotations.
- Update `docs/concepts/vector-search.md` to mention vector-column annotations
  next to the HNSW explanation.
- Add or adjust literalinclude anchors in the migration file so docs quote the
  actual annotation DDL instead of duplicating snippets.

### Chapter 3 - `schema-annotations-verification`

Add focused verification and close out project context.

Deliverables:

- Add an Oracle integration assertion that expected annotation rows exist in
  `USER_ANNOTATIONS_USAGE` after migration.
- Run the focused migration/integration check against Oracle 26ai.
- Run `make lint` and `make test` before implementation completion.
- Update `.agents/knowledge/guides/oracle-vector-search.md` or
  `.agents/patterns.md` only if implementation reveals a durable convention
  beyond this PRD.

---

## Global Constraints

- Keep SQL in `src/app/db/migrations/0001_cymball_coffee_products.sql`; do not
  create compatibility shim modules or app-runtime annotation readers.
- Preserve named SQL files under `src/app/db/sql/*.sql`; annotation queries used
  only by docs or tests may be inline in tests unless a production service needs
  them later.
- Use Oracle `:name` bind parameters if any runtime query is introduced.
- Do not persist browser coordinates or add geolocation metadata that implies
  coordinates are stored. Store annotations must reinforce request-scoped
  browser-coordinate privacy.
- Avoid docs-only unit tests. Runtime verification belongs in Oracle
  integration coverage and docs build/lint gates.

---

## Acceptance Criteria

- `coffee upgrade` / `python manage.py database upgrade --no-prompt` applies
  the existing baseline migration with inline annotation DDL on Oracle 26ai.
- No new migration file is created for this feature.
- `USER_ANNOTATIONS_USAGE` returns expected rows for representative table,
  column, and index annotations.
- Existing comments remain available in `USER_TAB_COMMENTS` and
  `USER_COL_COMMENTS`.
- Public docs explain what annotations demonstrate and include a working
  introspection query.
- `make lint` and `make test` pass before the implementation is called
  complete.

---

## Review Questions

No product decisions are blocked. Recommended defaults:

- Keep comments and add annotations rather than replacing comments.
- Use inline `ANNOTATIONS(...)` in the existing baseline DDL. SQLSpec's raw
  migration execution path is why inline Oracle syntax is acceptable even where
  the local SQL parser cannot model it.
- Keep annotation values human-readable strings or compact JSON strings only
  where multiple values are useful.

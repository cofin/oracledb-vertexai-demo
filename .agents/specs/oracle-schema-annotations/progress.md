# Progress: Oracle Schema Annotations

## Status

Inline DDL and docs updates are implemented locally. Focused unit coverage and
SQLSpec loader smoke pass. Oracle 26ai runtime migration verification is still
pending.

## Chapters

- [x] Chapter 1: `schema-annotations-ddl`
- [x] Chapter 2: `schema-annotations-docs`
- [ ] Chapter 3: `schema-annotations-verification`

## Notes

- SQLSpec migration execution uses raw SQL scripts, so unsupported sqlglot
  modeling of inline annotation syntax is not a planning blocker and should not
  force separate `ALTER` annotation statements.
- The existing baseline DDL in
  `src/app/db/migrations/0001_cymball_coffee_products.sql` now carries inline
  table, column, and supported normal-index annotations; no new migration was
  created.
- Oracle 26ai runtime verification is still required before full completion.

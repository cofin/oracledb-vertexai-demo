# Learnings: Oracle Schema Annotations

## 2026-06-13

- Oracle 26ai annotations should be demonstrated inline in the existing
  baseline DDL on this branch, not as a new follow-up migration and not as
  separate `ALTER ... ANNOTATIONS(...)` statements.
- SQLSpec migration loading preserves the named migration body and the runner
  executes SQL migrations as scripts, so local parser gaps in inline Oracle
  annotation syntax are not a reason to move annotations out of the DDL.
- Keep `COMMENT ON` statements for compatibility with existing metadata tools.
  Add annotations as the richer 26ai metadata surface for table, column, and
  documented normal-index metadata.
- The Oracle 26ai `CREATE VECTOR INDEX` docs do not document an
  `annotations_clause`; keep vector-index DDL focused on HNSW behavior and put
  model/dimension/task/distance metadata on the vector columns unless runtime
  verification proves a supported vector-index annotation placement.
- Verification run locally: `uv run pytest src/tests/unit/app/db/test_store_data_foundation.py -q`,
  SQLSpec loader smoke for `migrate-0001-up`/`migrate-0001-down`, and
  `make docs`. Oracle runtime migration smoke remains pending because it needs
  a clean Oracle 26ai schema.

## 2026-06-23

- Do not archive `oracle-schema-annotations` until a clean Oracle 26ai runtime
  migration has asserted the annotations in `USER_ANNOTATIONS_USAGE` or the
  repo's equivalent runtime metadata query. Static SQL/unit/docs checks are not
  enough for this flow's open verification gate.
- This flow still has no matching Beads epic, so archive or closeout work first
  needs Beads reconciliation before the markdown registry can be treated as
  complete.

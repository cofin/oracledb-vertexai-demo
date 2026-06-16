# Learnings: deadcode-sweep

## 2026-06-15 — Dead-code sweep (epic oracledb-vertexai-mzm.2, commit 1afc0c1)

- Re-audit before deletion paid off: the original sweep list flagged `EmbeddingCache`
  and `CacheService.delete_expired_responses` as dead, but a feature-level trace showed
  the embedding-cache feature is live (`get_embedding`/`save_embedding` called from
  `products/services.py`). Both were KEPT and are wired (typed read / cleanup command)
  in Ch8 instead. Lesson: grep "0 instantiations" is necessary but not sufficient —
  trace the feature, not just the symbol.

- `_SQLSpecPlugin` (empty top-level stub in `server/plugins.py`) is a distinct orphan
  from `_SQLSpecBase` (type alias used by the `db:` annotation) and `_SQLSpecPluginBase`
  (the real base of the nested `SQLSpecPlugin`). Whole-word grep with `_SQLSpecPluginBase`
  excluded was required to prove the stub was unreferenced.

- `CamelizedBaseStruct` use-count dropped 37 → 32 after the sweep. That is expected, not a
  regression: the 5 deleted structs (`ChatConversation`, `ChatConversationCreate`, and the
  three `_session.py` structs) each subclassed it. The KEEP requirement is that the symbol
  survives with its remaining live uses — verify by counting, not by raw "still present".

- Listener-discovery subsystem in `utils/domains.py` was fully dead because **no domain
  ships `events.py`/`listeners.py`**. Confirmed with `find src/app/domain -name events.py
  -o -name listeners.py` returning nothing. `_store_controller_results` was a single-caller
  private method → inlined into `_discover_and_register_controllers` rather than kept.

- `pydantic` half of `lib/schema.py` (`BaseSchema`/`CamelizedBaseSchema`/`camel_case`) was
  dead while the msgspec half (`CamelizedBaseStruct`) carries the live schema base. The
  word-boundary grep `\bBaseSchema\b` does NOT match `CamelizedBaseStruct` (different
  substring), so the acceptance grep correctly distinguishes the two.

- Named-SQL siblings must be deleted alongside their service method AND their
  `EXPECTED_KEYS` entry in `test_named_sql.py`, or `test_expected_named_query_loads`
  parametrizes over a key with no `.sql` definition. `EXPECTED_FILES` stays intact —
  `inventory.sql`/`stores.sql` retain other live queries, so no `.sql` file was deleted.

- Verification gate note: 2 unit tests in `src/tests/unit/tools/oracle/test_database.py`
  fail on this branch, but they are pre-existing failures tied to the unrelated uncommitted
  `tools/oracle/cli/database.py` apex work — NOT caused by this sweep. Proven by stashing
  only `database.py` and re-running: the failure persists at HEAD. The dead-code commit
  excludes all apex/database files; the rest of the unit suite (224 collected) passes.

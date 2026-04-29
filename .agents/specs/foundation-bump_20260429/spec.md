# Flow: Foundation Bump (foundation-bump_20260429)

*Chapter 1 of [cymbal-coffee-reset_20260429](../cymbal-coffee-reset_20260429/prd.md)*
*Beads epic: `oracledb-vertexai-4d6.1` (blocks Ch 2)*

---

## Specification

### Objective
Lay the new substrate for everything that follows: bump deps to current, switch the schema to **3072-dim FLOAT32 vectors with HNSW INMEMORY indexes** per Oracle 23ai best practices, align the embedding service with the new dim, regenerate fixtures, and confirm sqlspec's **native vector handlers** are wired so we never write `array.array('f', ...)` again.

### Code Analysis Summary

**Current state (verified 2026-04-29):**

- `pyproject.toml:20` — `sqlspec[adk,mypyc,oracledb,performance]==0.28.1`. **18 minor versions behind**; latest is 0.46.x.
- `pyproject.toml:24` — `google-adk` (no pin). Need explicit `2.0b1`.
- `pyproject.toml:30` — `sqlglot==27.29.0`. May need bump for sqlspec 0.46.
- `src/py/app/lib/settings.py:303` — `EMBEDDING_MODEL = "gemini-embedding-001"` ✅ already correct.
- `src/py/app/lib/settings.py:305` — `EMBEDDING_DIMENSIONS: int = 768` ❌ needs `3072`.
- `src/py/app/lib/settings.py:307` — `CHAT_MODEL = "gemini-2.5-flash"` ✅ already correct.
- `src/py/app/db/migrations/0001_cymball_coffee_products.sql`:
  - Lines 17, 65, 83 — three `VECTOR(768, FLOAT32)` columns (`product`, `embedding_cache`, `intent_exemplar`).
  - Lines 122-136 — three vector indexes using `ORGANIZATION NEIGHBOR PARTITIONS` (IVF), not HNSW.
  - Line 8-20 — `product` table has **no `INMEMORY` clause** (cache tables do at lines 55, 71, 89).
  - Line 74 — `embedding_cache.text_hash` comment says MD5 (project elsewhere uses SHA256).
- `src/py/app/domain/products/services/services.py:81-99` — `VertexAIService.get_text_embedding` calls `client.aio.models.embed_content(model=..., contents=text)` with **no `output_dimensionality`** and **no `task_type`**. With model default = 3072, this currently returns 3072-dim vectors that fail to insert into VECTOR(768) — the current code is in a broken/inconsistent state.
- `src/py/app/db/migrations/README.md:64` — references "VECTOR(768, FLOAT32)" — must update to 3072.
- `src/py/app/db/fixtures/` — 3 gzip files (`product.json.gz`, `intent_exemplar.json.gz`, `store.json.gz`) with embeddings encoded at 768 dims; must regenerate.
- **No `array.array(...)` sites in `src/py/app/`** — confirmed via grep. Sqlspec already accepts plain `list[float]`. Good. We just need to verify the new 0.46 native handlers are auto-registered (likely yes via `OracleAsyncConfig` defaults).
- `src/py/app/utils/serialization.py` — re-exports sqlspec's `numpy_array_*` hooks. Verify these are still exported by 0.46.

### Requirements

1. All five vector-related deps (`sqlspec`, `google-adk`, `google-genai`, `python-oracledb`, `sqlglot`) at current/target versions and locked.
2. The 0001 baseline migration uses `VECTOR(3072, FLOAT32)`, marks `product` `INMEMORY`, and creates **HNSW INMEMORY** vector indexes (not IVF).
3. `lib/settings.py` `EMBEDDING_DIMENSIONS = 3072`; `VertexAIService.get_text_embedding` passes `output_dimensionality` and a `task_type` parameter (defaults to `RETRIEVAL_DOCUMENT`, callers querying use `RETRIEVAL_QUERY`).
4. Fresh fixtures with 3072-dim embeddings committed and load cleanly into the new schema.
5. Operational docs (`tools/oracle/`, migrations README) document `vector_memory_size >= 4G` requirement.
6. `make install && make lint && make test` green from a clean clone with the new substrate.
7. **Zero** `array.array(...)` sites or hand-rolled vector serialization in app code (audit confirmed already clean — keep it that way).

### Acceptance Criteria

- `uv lock` reflects bumped versions; `uv sync` succeeds.
- `EXPLAIN PLAN FOR SELECT * FROM product ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST 5 ROWS ONLY` shows `VECTOR INDEX RANGE SCAN` against `product_embedding_idx` (HNSW), not full table scan or IVF.
- `SELECT NAME, BYTES FROM V$SGAINFO WHERE NAME LIKE '%Vector%'` returns a non-zero `Vector Memory` allocation after restart.
- `uv run app run` boots without errors, chat endpoint returns a real Vertex AI response, vector search returns ≥1 product result.
- A Python REPL `import sqlspec; print(sqlspec.__version__)` reports 0.46.x.
- Fixture file sizes documented (expected ~4× larger than 768-dim originals).

### Risks / Known Gotchas

- `sqlspec` 0.46 may have breaking import paths vs 0.28 — audit each `from sqlspec...` import after bump.
- `google-adk==2.0b1` is **beta**; pin exactly. Some 1.x APIs disappear; isolate behind `app/domain/chat/services/adk.py`. (Full migration is Ch 3 — Ch 1 only needs ADK to import without crashing the app boot.)
- Oracle container may need restart after setting `vector_memory_size` — document the ALTER SYSTEM + bounce.
- `output_dimensionality=3072` is the **default** for `gemini-embedding-001` and produces **pre-normalized** vectors; if anyone changes the dim later, they must L2-normalize client-side (note in patterns.md).
- Fixture file size: ~4× growth at 3072 dims. **Verified 2026-04-29**: `intent_exemplar.json.gz` is **1019 records at 768 dims, 7.0 MB gzipped** (not anomalous — ~7 KB/row of JSON-encoded floats compresses cleanly). Expected 3072-dim regen: ~25–28 MB gzipped, still git-friendly. `product.json.gz` smaller (47 rows). User had hypothesised the file might already be at 3072 dims — confirmed otherwise; regeneration is required.
- `current_price` mismatch in `services.py:47` (column is `price` in DDL) is a **Ch 2 problem**, not Ch 1. Note it in Ch 2 Beads notes.

---

## Implementation Plan

### Phase 1: Dependency Bump

- [x] **1.1** Update `pyproject.toml` deps: (`oracledb-vertexai-4d6.1.1`)
  - `sqlspec[adk,mypyc,oracledb,performance]==0.28.1` → `sqlspec[adk,mypyc,oracledb,performance]>=0.46,<0.47`
  - `google-adk` → `google-adk==2.0.0b1`
  - `google-genai` → `google-genai>=1.0` (or current latest)
  - Add explicit `python-oracledb>=3.4,<4` (currently transitive via sqlspec).
  - `sqlglot==27.29.0` → check sqlspec 0.46's required range; bump to satisfy. (Likely 27.x or 28.x; verify via `uv add sqlspec` dry-run after bump.)
- [x] **1.2** Run `uv lock --upgrade` then `uv sync`. Resolve conflicts.
- [x] **1.3** Smoke test: `uv run python -c "import sqlspec, google.adk, google.genai; print(sqlspec.__version__, google.adk.__version__)"` — expect `0.46.x` and `2.0.0b1`.
- [x] **1.4** Audit imports across `src/py/app/` — `grep -rn "from sqlspec" src/py/app/` and confirm each path still resolves under 0.46. Common moves: `sqlspec.driver` → `sqlspec.driver.adapter_base`; check `sqlspec.adapters.oracledb.litestar.OracleAsyncStore`.

### Phase 2: Schema Rewrite (`src/py/app/db/migrations/0001_cymball_coffee_products.sql`)

This is a **reference app** with a single baseline migration; we modify in place rather than adding a versioned drift migration.

- [x] **2.1** Replace all three `VECTOR(768, FLOAT32)` → `VECTOR(3072, FLOAT32)`: (`oracledb-vertexai-4d6.1.2`) — `[b599aa1]`
  - Line 17: `product.embedding`
  - Line 65: `embedding_cache.embedding`
  - Line 83: `intent_exemplar.embedding`
- [x] **2.2** Update column/table comments referencing 768:
  - Line 23: `'768-dimensional embedding vector for semantic search'` → `'3072-dimensional gemini-embedding-001 vector'`
  - Line 75: `'768-dimensional embedding vector'` → `'3072-dimensional gemini-embedding-001 vector'`
  - Line 74: `'MD5 hash of input text'` → `'SHA256 hash of input text'`
- [x] **2.3** Add `INMEMORY PRIORITY HIGH` clause to the `product` `CREATE TABLE` statement (line 8-20). Preserves base-table fetch in RAM after the index hit.
- [x] **2.4** Replace the three IVF index DDLs (lines 122-136) with HNSW INMEMORY:
  ```sql
  CREATE VECTOR INDEX product_embedding_idx ON product (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH
  DISTANCE COSINE
  WITH TARGET ACCURACY 95
  PARAMETERS (TYPE HNSW, NEIGHBORS 40, EFCONSTRUCTION 500);
  ```
  Apply the same shape to `intent_exemplar_embedding_idx` and `embedding_cache_embedding_idx`. Same `NEIGHBORS=40`, `EFCONSTRUCTION=500`, `TARGET ACCURACY=95` for all three.
- [x] **2.5** Update the `migrate-0001-down` section (lines 254-258) — drop statements still work for HNSW indexes, but verify no IVF-specific syntax remains.
- [x] **2.6** Update `src/py/app/db/migrations/README.md`:
  - Line 64: `VECTOR(768, FLOAT32)` → `VECTOR(3072, FLOAT32) (gemini-embedding-001)`
  - Add a new section "Vector Memory Pool" describing the `vector_memory_size >= 4G` requirement and how to set it.

### Phase 3: Vector Memory Pool Operational Docs

- [x] **3.1** Find the Oracle container/setup script under `tools/oracle/` (`oracledb-vertexai-4d6.1.3`) that initializes the dev container. Add an `ALTER SYSTEM SET vector_memory_size = 4G SCOPE=SPFILE;` step followed by a documented restart instruction. — `[f99de69]`
- [x] **3.2** If no such script wraps init (likely just `docker run`), create `tools/oracle/configure_vector_memory.sql` containing the ALTER SYSTEM + a `STARTUP FORCE;` and reference it from `migrations/README.md` and the root `README.md` setup section.
- [x] **3.3** Verify post-restart with `SELECT NAME, BYTES FROM V$SGAINFO WHERE NAME LIKE '%Vector%';` showing the allocated pool. Document this verification command in `migrations/README.md`.

### Phase 4: Settings + VertexAI Service Alignment (`oracledb-vertexai-4d6.1.4`)

- [x] **4.1** `src/py/app/lib/settings.py:305` — change `EMBEDDING_DIMENSIONS: int = 768` to `EMBEDDING_DIMENSIONS: int = 3072`. — `[2bbaddb]`
- [x] **4.2** `src/py/app/domain/products/services/services.py:88-99` — modify `VertexAIService.get_text_embedding` signature and call:
  ```python
  from google.genai.types import EmbedContentConfig

  async def get_text_embedding(
      self,
      text: str,
      *,
      task_type: str = "RETRIEVAL_DOCUMENT",
      return_cache_status: bool = False,
  ) -> Any:
      cached = await self.cache_service.get_embedding(text, self.embedding_model)
      if cached:
          return (cached, True) if return_cache_status else cached

      response = await self.client.aio.models.embed_content(
          model=self.embedding_model,
          contents=text,
          config=EmbedContentConfig(
              task_type=task_type,
              output_dimensionality=settings.vertex_ai.EMBEDDING_DIMENSIONS,
          ),
      )
      ...
  ```
  Keep the cache + post-call save logic intact.
- [x] **4.3** Update the one query-path caller (`OracleVectorSearchService.similarity_search`, ~line 105 in same file) to pass `task_type="RETRIEVAL_QUERY"` for the user-query embed. Storage path (the `bulk-embed` CLI) keeps the `RETRIEVAL_DOCUMENT` default.
- [x] **4.4** Verify sqlspec's native Oracle vector handlers register automatically when `OracleAsyncConfig` is constructed (config.py:55-58). If 0.46 requires explicit opt-in, add `extension_config={"oracle": {"register_numpy_handlers": True}}` to `db = _settings.db.create_config()`. Test by inserting a `list[float]` literal via REPL. — verified by inspection: `register_numpy_handlers` called from `OracleAsyncConfig` at `config.py:320, 507`. No opt-in needed.
- [-] **4.5** Drop the redundant `numpy>=2.3.3` direct dep from `pyproject.toml:27` if sqlspec 0.46 already pulls it as an extra. (Run `uv tree | grep numpy` to verify.) — skipped per user pyproject reduction at `f54dfbf` (numpy retained intentionally).

### Phase 5: Fixture Regeneration (`oracledb-vertexai-4d6.1.5`)

- [x] **5.1** Stop and recreate the dev DB: `make stop-infra && make start-infra` (waits for Oracle to be ready). Apply the `vector_memory_size` setting from Phase 3. — `[8f77ed7]`
- [x] **5.2** Apply migration: `uv run app db upgrade`. Confirm tables and HNSW indexes were created (query `USER_INDEXES` for `product_embedding_idx` and verify `INDEX_TYPE` mentions VECTOR). — All three vector indexes present (`PRODUCT_EMBEDDING_IDX`, `INTENT_EXEMPLAR_EMBEDDING_IDX`, `EMBEDDING_CACHE_EMBEDDING_IDX`); `INDEX_TYPE = VECTOR`.
- [x] **5.3** Audit `src/py/app/utils/fixtures.py` `FixtureLoader` for column mismatch handling — when loading the existing 768-dim fixtures into a 3072 schema, the embedding column will fail. Either:
  - **Option A (preferred)**: Modify the loader to skip columns whose dim mismatches and emit a warning. Then run `bulk-embed --force` after load.
  - **Option B**: Add a `--skip-embeddings` flag to `db load-fixtures` for one-shot rebootstrap.
  Pick Option A (simpler — embeddings get re-generated unconditionally on dim change). — Implemented via `FixtureProcessor(expected_vector_dim=N)` in `[dd7e9b0]`. 5 unit tests cover the skip-with-warning behavior.
- [x] **5.4** Load text fixtures: `uv run app db load-fixtures` (skipping embeddings). — Loaded 1156 records (15 store, 122 product, 1019 intent_exemplar); single dim-mismatch warning emitted.
- [ ] **5.5** Regenerate product embeddings: `uv run app coffee bulk-embed --force`. Confirms 3072-dim vectors are produced and inserted. — DEFERRED: needs a real Vertex AI project; `.env` currently has `VERTEX_AI_PROJECT_ID=demo-project`. CLI is wired and ready; resume on a host with GCP credentials.
- [x] **5.6** Regenerate intent_exemplar embeddings: extend `bulk-embed` with `--target intent_exemplar` flag, OR write a one-off `tools/regen_intent_embeddings.py` that runs the same loop on the `intent_exemplar` table. (Bias toward extending `bulk-embed` since it's the lifecycle command.) — Wired as `bulk-embed --include-exemplars` in `[dd7e9b0]`; runtime regen blocked on the same Vertex project deferral as 5.5.
- [ ] **5.7** Export fresh fixtures: `uv run app coffee export-fixtures`. Replaces `product.json.gz` and `intent_exemplar.json.gz` with 3072-dim versions. Investigate the suspiciously large `intent_exemplar.json.gz` (7.2 MB at 768 dims — likely indented JSON or duplicate records); if it grows to >50 MB at 3072 dims, optimize export (no indenting, deduplicate). — DEFERRED: gated on 5.5 / 5.6.
- [~] **5.8** Sanity-check fixture round-trip: drop tables, re-load fresh fixtures, query `SELECT COUNT(*), VECTOR_DIMS(embedding) FROM product;` and `intent_exemplar;` — expect `(N, 3072)` for both. — `VECTOR_DIMS = 3072` confirmed for both tables via dummy zero-vector smoke insert; full fresh-fixture round-trip deferred until 5.5/5.6/5.7 land.
- [ ] **5.9** `git add` the new fixtures; check `git status` shows replaced files only (no schema migrations created/renamed). — DEFERRED: no new fixtures to commit yet.

### Phase 6: Verification (`oracledb-vertexai-4d6.1.6`)

- [x] **6.1** `make lint` — clean. — Pre-commit (ruff + checks) passed on all touched files.
- [~] **6.2** `make test` — all unit + integration tests pass against the new schema. — Unit suite (10/10) green including 5 new `test_fixture_loader_dim_skip` tests. Integration suite deferred until live embeddings are available.
- [ ] **6.3** `uv run app run` — app boots; check logs for ADK 2.0b1 startup messages and no import errors. — DEFERRED: app run currently needs the Vertex AI client to initialize; gated on 5.5.
- [ ] **6.4** Manual smoke (curl or browser):
  - `POST /api/chat` → returns a real Gemini response.
  - The vector search invoked by the chat agent returns ≥1 product (chat tool path).
  - Intent classification still works (Ch 3 will replace it; for Ch 1, it must keep returning a label).
  DEFERRED: gated on 5.5 / 5.6 (needs populated embeddings).
- [x] **6.5** EXPLAIN PLAN check: in sqlplus, run
  ```sql
  EXPLAIN PLAN FOR
  SELECT id, name FROM product
  ORDER BY VECTOR_DISTANCE(embedding, :v, COSINE)
  FETCH APPROX FIRST 5 ROWS ONLY WITH TARGET ACCURACY 95;
  SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);
  ```
  Capture output in the Beads task notes; expect `VECTOR INDEX RANGE SCAN` against `product_embedding_idx`. — Confirmed via DBMS_XPLAN: `VECTOR INDEX HNSW SCAN` against `PRODUCT_EMBEDDING_IDX` with the migrated baseline (HNSW INMEMORY produces an HNSW SCAN row instead of RANGE SCAN; semantically equivalent for the index-usage check).

### Phase 7: Patterns.md Snapshot (`oracledb-vertexai-4d6.1.7`)

- [x] **7.1** Update `.agents/patterns.md` "Architecture Patterns / SQLSpec" section: append a line documenting the canonical Oracle vector index recipe (`HNSW INMEMORY, NEIGHBORS=40, EFCONSTRUCTION=500, TARGET ACCURACY=95`) and `vector_memory_size >= 4G` requirement. — Captured in `[8467d2f]` along with Free Edition's 512M reality (the 4G floor only applies to Standard/Enterprise/Autonomous).
- [-] **7.2** Remove the obsolete gotcha about `make test .ONESHELL` false-green (the underlying issue is fixed in current Makefile). — Skipped: gotcha left in place; the `.ONESHELL` line is still useful as historical context and was not blocking.
- [x] **7.3** Add new gotcha: "Embedding dim must match `VECTOR(N)` schema; mismatched dims silently fail at insert. `EMBEDDING_DIMENSIONS` setting and DDL are a coupled contract." — Added in `[8467d2f]`.
- [x] **7.4** Update gotcha about Oracle boolean nullability — note that `product.in_stock` is `DEFAULT TRUE` but still nullable; the `NVL(in_stock, TRUE)` workaround in queries stays until Ch 2 normalizes the schema. (Ch 5 will collapse this further.) — Existing gotcha left intact since current behavior already documents the workaround; no change needed for Ch 1.

---

## Out of Scope (defer to other chapters)

- **`SQLSpecAsyncService` base class introduction** — Ch 2.
- **Inline-SQL → named SQL files** — Ch 2.
- **4 Dishka providers → 1** — Ch 2.
- **ADK 2.0 graph workflow migration of the runner** — Ch 3 (Ch 1 only ensures ADK 2.0b1 imports cleanly).
- **Parallel intent classification + Gemini structured output** — Ch 3.
- **Frontend rebuild** — Ch 4.
- **CLI trim (`bulk-embed`, `export-fixtures` deletion)** — Ch 5 (Ch 1 still needs them for fixture regen).
- **Knowledge base consolidation** — Ch 5.

# Master PRD: Demo Simplification & Contract Cleanup

*PRD ID: `demo-simplification`*
*Created: 2026-06-14*
*Beads: `oracledb-vertexai-mzm` (master epic)*
*Research: [`../../research/research_demo_simplification/research.md`](../../research/research_demo_simplification/research.md)*
*Absorbs: `settings-config-consolidation_20260501`*

---

## North Star

Make the Cymbal Coffee demo **maximally readable for a reader with high Oracle-DB
expertise but low Python experience**. Concretely:

- Delete all dead code, fluff/filler comments, and legacy compatibility code.
- Collapse duplicate paths to one obvious path: **one streaming chat route**, **one
  no-key Maps URL builder**, **folded ADK helper modules**.
- Reduce `src/app/lib/settings.py` to a small, typed, effectively-immutable, quiet
  configuration contract that reflects only what the app actually uses.
- Make **every doc 100% accurate** — no outdated or hallucinated references.

**Behavior is preserved** end-to-end, with one deliberately-chosen addition: chat
store replies render a "Get directions" Maps link alongside the existing search link.

---

## Resolved Decisions (2026-06-14, user-confirmed)

1. **`/api/chat`** — delete the non-streaming route entirely; keep only `/api/chat/stream`.
   Cascade-retire `process_request`, `CoffeeChatReply`, `metrics_badges`, and the dead partials.
2. **Maps** — consolidate to one builder (`products/services/maps.py`) **and render directions**
   (the feature is already live via a duplicate inline builder in `_adk_grounding.py`).
3. **ADK modules** — fold `_adk_history` + `_adk_telemetry` back into `adk.py`; keep `_adk_grounding`.
4. **Test infra** — unchanged. The project deliberately uses its own `tools/`-managed Oracle
   container with data-level isolation (migrate → truncate → reseed per worker), **not**
   pytest-databases. WS6 is test-readability only.
5. **Settings** — this PRD **absorbs** `settings-config-consolidation_20260501`; its six
   chapters compress into Ch3/Ch4/Ch8 here.

---

## Current State (verified)

All findings below are grep-verified against current source (see research doc "Verified Evidence").

- `domain/chat/services/adk.py` is 1,165 LOC (3× the next file), carries `# noqa: PLR0914`,
  has a dead method (`record_search_metric`), a duplicated PRODUCT_RAG path, ~8 single-call
  private event-builders, and three orbiting `_adk_*` modules.
- Verified-dead, zero-caller: `ServerSettings`/`AgentSettings`/`CacheSettings` (+ unused knobs),
  `utils/sync_tools.py`, `lib/exceptions.py::ApplicationError`, the pydantic half of `lib/schema.py`,
  the listener-discovery subsystem in `utils/domains.py`, dead store-query methods, dead schema structs.
- Docs: `AGENTS.md`/`CLAUDE.md` (symlinked) instruct `task_type=RETRIEVAL_*` — the code uses
  `embedding_purpose`; model name is stale everywhere; fixture counts wrong (122/16 → 130/17);
  store/inventory/maps documented as "planned" though shipped.
- `POST /api/chat` is unreached by the UI (the form posts only to `/api/chat/stream`).
- The Maps feature works through a **duplicate** inline builder; `products/services/maps.py` is orphaned.

---

## Global Constraints (binding for every chapter)

1. **No backwards-compat shims, ever** — delete old code completely (no re-exports, deprecation
   stubs, or `if legacy:` branches).
2. **Docstrings/comments describe behavior only** — brief; never reference specs, PRDs, phases,
   or flow IDs.
3. **No dead code** — if a symbol becomes unused after a change, delete it (and its named-SQL
   sibling and tests) in the same chapter.
4. **Preserve behavior** — no user-facing change except the Maps directions link (Ch7).
5. **Preserve public env var names** — `DATABASE_*`, `WALLET_*`, `TNS_ADMIN`, `SECRET_KEY`,
   `LITESTAR_*`, `VERTEX_AI_*`, `GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `VITE_*`, `ASSET_URL`.
6. **Coordinate privacy** — browser coordinates stay request-scoped; never persisted in history,
   cache, metrics, or logs. No-key Maps URL behavior stays the default.
7. **Gate** — `make lint && make test` must be green at the end of every chapter.
8. **Audience** — favor explicit, linear, obvious code over clever abstraction.
9. `src/app/ioc.py` must not use `from __future__ import annotations` (Dishka runtime annotations).

---

## Roadmap

Ordered risk-ascending / dependency-correct. `make lint && make test` gates each chapter.

| Ch | Flow (`slug`) | Beads | Depends on | Risk |
|----|---------------|-------|-----------|------|
| 1 | Documentation accuracy (`docs-accuracy`) | `mzm.1` | — | none |
| 2 | Dead-code sweep (`deadcode-sweep`) | `mzm.2` | — | low |
| 3 | Settings audit + factory (`settings-audit-and-factory`) | `mzm.3` | — | med |
| 4 | Settings/tools DB env contract (`settings-database-env-contract`) | `mzm.4` | Ch3 | med |
| 5 | Chat-path consolidation (`chat-path-consolidation`) | `mzm.5` | — | med |
| 6 | ADK readability (`adk-readability`) | `mzm.6` | Ch5 | med |
| 7 | Maps consolidation + directions (`maps-consolidation`) | `mzm.7` | Ch6 | low |
| 8 | Settings AI/chat/web/log (`settings-ai-chat-web-log`) | `mzm.8` | Ch3, Ch6 | med |
| 9 | Frontend cleanup (`frontend-cleanup`) | `mzm.9` | Ch5, Ch7 | low |
| 10 | Test simplification (`test-simplification`) | `mzm.10` | Ch6, Ch8, Ch9 | med |

**Why this order.** Docs first because fixing the `task_type` error removes a trap that would
misdirect agent-assisted work on every later chapter. Pure deletions next (mechanical, low risk).
Settings factory/immutability before the AI/chat settings wiring, because the field rename touches
every consumer. Chat-path retire before ADK readability because both edit `adk.py` and retiring
`process_request` shrinks what the refactor must touch. Settings AI/chat wiring lands after the
ADK refactor so it wires into clean code. Frontend after the dead partials (Ch5) and the directions
action (Ch7) exist. Tests last, once the code shape is final.

Each chapter's implementation-ready worksheet lives in `.agents/specs/<slug>/spec.md`.

---

## Settings absorption map

`settings-config-consolidation_20260501` → this PRD:

| Old settings chapter | Lands in |
|---|---|
| Ch1 contract audit (tests) | Ch3 (`settings-audit-and-factory`) |
| Ch2 core factory (immutable, lowercase, shell-env, quiet) | Ch3 |
| Ch3 database env contract | Ch4 (`settings-database-env-contract`) |
| Ch4 AI/chat/cache (AISettings, ChatSettings) | Ch8 (`settings-ai-chat-web-log`) |
| Ch5 web/log cleanup | Ch8 |
| Ch6 docs/env verification | distributed into each settings chapter's acceptance |

The old spec folder stays as a historical artifact; `flows.md` marks it absorbed. Deviation from
its Review Defaults: the lowercase internal-field rename is retained as a goal but is the
lowest-priority item — if it threatens scope, ship the dead-knob deletion + immutability + quiet
factory and leave the rename.

---

## Global Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Many chapters edit `adk.py` → merge churn | Strict sequence Ch5 → Ch6 → Ch8; one chapter in flight at a time on `adk.py`. |
| Removing the PRODUCT_RAG re-ground branch changes streamed output | Integration test asserts PRODUCT_RAG stream output is unchanged before/after (Ch6). |
| Settings field rename breaks consumers | Single focused pass with `rg` for old names; tests-first lock in Ch3. |
| Deleting `/api/chat` breaks an external consumer | None found (only generated `openapi.json`); final grep for `/api/chat"` POSTs before removal (Ch5). |
| Doc edits introduce new inaccuracies | Every edited claim grep-verified against source; the `docs/_build` self-correction is the cautionary precedent (Ch1). |
| Maps consolidation changes `map_actions` shape | New builder must emit the same `{type,label,url}` shape; covered by `test_maps.py` + a grounding assertion (Ch7). |
| Aggressive test pruning drops real coverage | Replace each deleted private-surface test with a public-behavior test; keep the `_make_tool_factories`/`_build_workflow` seams (Ch10). |

---

## Out of Scope

- New chat features, new intent labels, or schema changes (beyond settings field renames).
- Re-platforming test infrastructure (Decision 4).
- Anything in `docs/_build/` (gitignored build artifact, not tracked).

---

## Re-audit Corrections (2026-06-14)

After a feature-level re-verification of every "dead" item:

- **`EmbeddingCache` struct — KEEP, do not delete.** The embedding-cache feature is live
  (`CacheService.get_embedding`/`save_embedding`, used alongside the response cache). The
  struct is simply never typed-in because `get-cached-embedding` selects only `embedding`.
  Ch8 wires it (full-row read → `schema_type=EmbeddingCache`), making it live and symmetric
  with `ResponseCache` instead of deleting it.
- All other dead items re-confirmed at the feature level (search city/state/zip → served by
  `find_stores_by_location`; metrics → `MetricsService.record_search`; history → `ChatMessage`;
  `get_store_inventory` test-only with live inventory = `ProductAvailability`; `_SQLSpecPlugin`
  is an empty orphan distinct from `_SQLSpecBase`/`_SQLSpecPluginBase`; no domain ships listeners).

### Resolved cache decisions (2026-06-14, user-confirmed)
1. **`delete_expired_responses` — keep + wire** (not delete). Ch8 wires it into a cache-cleanup
   command (`coffee clear-cache` extension or a `coffee prune-cache`); the deadcode-sweep leaves
   it and its test intact.
2. **`EMBEDDING_CACHE_ENABLED` — delete the dead flag.** It dies with `CacheSettings` in Ch3; the
   embedding cache stays unconditionally on (no bypass branch added).

## Status — COMPLETE (2026-06-15)

- [x] Research complete and decisions resolved.
- [x] Beads master epic + 10 chapter epics + dependency graph + notes created.
- [x] All 10 chapter `spec.md` worksheets refined to implementation-ready.
- [x] **All 10 chapters implemented, committed, and Beads-closed** (`06d6338`..`f5298f2`).

### Final gate results
- `make lint`: GREEN (ruff + mypy/basedpyright "0 errors" + frontend type checks).
- Unit suite: **248 passed**; the only 2 failures (`tools/oracle/test_database.py`) are **pre-existing and unrelated** (verified: they fail against the pre-implementation `tools/oracle/` code and the separate ORDS WIP), not caused by any chapter.
- Integration suite (Oracle-backed): **28 passed / 0 failed** — chat streaming, RAG workflow, maps, pages all green.
- Chat path (Ch5/Ch6) and maps/settings (Ch7/Ch8) validated end-to-end against real Oracle.

### Per-chapter commits
`06d6338` docs · `1afc0c1` deadcode · `89efd7a` settings-factory · `31485ce` db-env-contract · `7b96981` chat-path · `9f528ab` adk-readability · `c3f5704` maps · `d2d960a` settings-ai-chat · `09a426d` frontend · `adb7aba` tests (+ flow-sync chore commits).

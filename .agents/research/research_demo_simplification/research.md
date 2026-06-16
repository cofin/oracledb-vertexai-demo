# Research: Simplify & De-Cruft the Cymbal Coffee Demo (backend, frontend, docs, tests)

**Workspace**: `.agents/research/research_demo_simplification/`
**Status**: Complete
**Type**: Refactoring
**Date**: 2026-06-14
**Branch**: `feat/inv`

> **Goal (verbatim intent):** Make the demo maximally readable for an audience with **high Oracle expertise but low Python experience**. Simplify / remove / re-order without breaking functionality; inline private methods used once; strip all dead code and fluff/filler comments; make docs **100% accurate** with zero outdated/hallucinated references; remove "legacy" compatibility code (accepting a test overhaul).

---

## Executive Summary

- **One file dominates the readability problem.** `domain/chat/services/adk.py` (1,165 LOC) plus its three satellite modules (`_adk_grounding`, `_adk_history`, `_adk_telemetry`) hold most of the complexity. It contains one fully-dead method, a duplicated PRODUCT_RAG path, a 137-line `stream_request` carrying `# noqa: PLR0914`, and ~8 single-call private event-builders. This is the single highest-leverage target.
- **A large, low-risk dead-code surface exists across `lib/` and `utils/`.** Verified dead: `ServerSettings` / `AgentSettings` / `CacheSettings` (3 whole dataclasses, 0 references), `utils/sync_tools.py` (0 importers), `lib/exceptions.py::ApplicationError` (0 references), the pydantic half of `lib/schema.py` (`CamelizedBaseSchema`/`BaseSchema`/`camel_case`/`BaseStruct.to_dict` = 0 uses), the listener-discovery subsystem in `utils/domains.py`, dead schema structs (`_session.py`), and dead store-query methods (`find_stores_by_city/state`, `search_stores_by_zip`, `get_store_inventory`, `_location.py::location_hint_matches`). None have production callers. **Correction (2026-06-14):** `_cache.py::EmbeddingCache` is NOT dead-and-deletable — the embedding-cache *feature* is live (`CacheService.get_embedding`/`save_embedding`); the struct is merely un-typed-in and gets wired in Ch8, not deleted.
- **The docs contain real, load-bearing inaccuracies.** The canonical agent file `AGENTS.md`/`CLAUDE.md` (symlinked) instructs `task_type="RETRIEVAL_QUERY/DOCUMENT"` — **the code uses no `task_type` at all**; it uses `embedding_purpose` + a text instruction prefix. Every doc names the model `gemini-embedding-2`; the code literal is `gemini-embedding-2-preview`. Fixture counts are wrong (docs say 122 products / 16 stores; reality is **130 / 17**). Store/Inventory/Maps are described as "planned" but are fully implemented and shipping.
- **The "legacy/compat" surface to delete is small and well-bounded.** Only two genuine compat shims exist: `workflow.py::make_coffee_node`'s `hasattr(agent, "model_copy")` dual-path, and `tools/lib/utils.py::migrate_sqlcl_connection` (renames old `mcp_demo`→`cymbal_coffee`). Most other "fallback" hits are legitimate domain behavior (vector-search fallback) and must be kept.
- **The test work is readability, not re-platforming.** The suite intentionally does **not** use pytest-databases; integration tests run against the repo-managed Oracle container (`tools/` + `make start-infra`) with data-level isolation (`integration/conftest.py` does migrate → idempotent bootstrap → truncate → reseed per xdist worker). That design stays. The real overhaul target is `test_adk.py` (1,075 LOC ≈ 20% of the suite), which over-tests private internals, plus deletion-guard tests and `@pytest.mark.asyncio`→`anyio` drift.
- **Self-correction (modeling the no-hallucination bar):** an early hypothesis that `docs/_build/html/` was *committed* and the #1 source of stale references was **false** — that tree is gitignored (`.gitignore` covers `docs/_build/`) with **0 tracked files**. No action needed there. This is recorded as a reminder that every doc/code claim in the follow-on work must be grep-verified, not assumed.

---

## Research Tasks Summary

| Task | Status | Key Findings |
|------|--------|--------------|
| ADK chat service deep-dive | Complete | 1 dead method, duplicated PRODUCT_RAG path, `stream_request` refactor, ~8 inline-able privates, `_adk_*` split is net-negative |
| Products / System / Web domains | Complete | 4 dead store methods, dead `maps.py` (orphaned), dead schemas, fluff docstrings, nested-ternary readability |
| Infra (lib/server/cli/utils/settings/config) | Complete | 3 dead settings dataclasses + ~8 dead knobs, 2 dead files, dead listener subsystem, lazy-init scaffolding tax |
| Docs accuracy audit | Complete | `task_type` wrong, model-name stale everywhere, wrong fixture counts, "planned" features already shipped, ADK version wrong |
| Tests + legacy removal | Complete | pytest-databases absent, `test_adk.py` over-mocks privates, 2 real compat shims, `asyncio`→`anyio` drift |
| Frontend templates/assets | Complete | Dead non-stream `/api/chat` HTML path + 3 dead partials, duplicated welcome/EXPLAIN-PLAN render, `main.js` monolith |

---

## Verified Evidence (headline claims, directly grep-confirmed)

| Claim | Evidence | Verdict |
|-------|----------|---------|
| `task_type` not used; code uses `embedding_purpose` | `services.py:36,276,301-304`, `adk.py:147,314`, `cli/_helpers/embeddings.py:131`; CLAUDE.md/AGENTS.md:161-163 say `task_type` | Docs **WRONG** |
| Model literal is `gemini-embedding-2-preview` | `settings.py:349`, `services.py:35`; docs say `gemini-embedding-2` | Docs **STALE** |
| Fixtures = 130 products / 17 stores | `product.json.gz`=130, `store.json.gz`=17; `store_product_inventory.json.gz` exists | Docs say 122/16 → **WRONG** |
| `record_search_metric` is dead | `adk.py:210` is the only occurrence repo-wide | **DEAD** |
| `ServerSettings`/`AgentSettings`/`CacheSettings` dead | 0 references to classes or `settings.server/agent/cache` outside `settings.py` | **DEAD** |
| `utils/sync_tools.py` dead | Only "ref" is `from sqlspec.utils.sync_tools import run_` (library, not app module) | **DEAD** |
| `ApplicationError`, `BaseStruct.to_dict`, pydantic schema classes dead | `ApplicationError`=0, `.to_dict()`=0, `CamelizedBaseSchema`/`BaseSchema`/`camel_case`=0 (only `CamelizedBaseStruct`=37 alive) | **DEAD** |
| `_session.py` structs dead (`UserSession`/`UserSessionCreate`/`HistoryMeta`) | Never constructed/mapped; live history returns `ChatMessage`, live session = Litestar plugin + `app_session` table | **DEAD** |
| `_cache.py::EmbeddingCache` | embedding-cache feature live (`get_embedding`/`save_embedding` called from `products/services.py:279,295`); struct just un-typed-in | **KEEP + wire (Ch8)** |
| Dead store methods | `find_stores_by_city/state`, `search_stores_by_zip` = def-only (0 tests even); `location_hint_matches`=0 refs | **DEAD** |
| `make_coffee_node` compat shim | `workflow.py:41-42` `if hasattr(agent, "model_copy")` dual-path | **COMPAT** |
| `/api/chat` non-stream route unreached by UI | Only `/api/chat/stream` is posted (`chat.html.j2:73`); non-stream still in `openapi.json` | **DEAD from UI** (API contract = open question) |
| `pytest-databases` absent (by design) | 0 hits in `pyproject.toml`; tests use `tools/`-managed Oracle + data-level reset (`integration/conftest.py`) | **Intentional** |
| `/api/chat` (non-stream) `process_request` has no app caller | `process_request` called only at `_chat.py:96`; `stream_request` is independent | **DEAD on `/api/chat` delete** |
| Maps already live via grounding duplicate | `_adk_grounding.py:186-201` builds `map_actions`; `main.js:694-754` renders them; `maps.py` orphaned | **DUPLICATE builder** |
| `docs/_build/html/` is NOT committed | `git check-ignore` matches; `git ls-files docs/_build` = 0 | Early hypothesis **REFUTED** |
| `CLAUDE.md` is a symlink to `AGENTS.md` | `ls -la` shows `CLAUDE.md -> AGENTS.md` | Edit `AGENTS.md` once = both fixed |

---

## Codebase Analysis

The work decomposes into six independent workstreams. Each is sized for its own follow-on flow.

### WS1 — `adk.py` & ADK chat services (highest leverage)

**Dead code**
- `adk.py:210-232` `record_search_metric` — 0 callers, never wired into `_make_tool_factories` (514-522). Carries a redundant local re-import of `SearchMetricsCreate` (already imported at line 60). **Delete the method.** *(risk: none)*

**Duplication / simplify**
- `adk.py:1081-1087` — PRODUCT_RAG is re-grounded inside `stream_request` even though `_deterministic_route_event` (930) already routes PRODUCT_RAG via `_product_rag_event` (687) and `return`s (1039-1041). The fan-out re-ground branch is unreachable for PRODUCT_RAG; once removed, the ADK `Runner`/`Workflow` tail only ever serves GENERAL_CONVERSATION — which should be stated plainly. *(risk: low — confirm classifier vs `_effective_intent` cannot diverge post-fanout)*
- `adk.py:985-1121` `stream_request` — 137 lines, `# noqa: PLR0914`, three interleaved exits (cache-hit, deterministic route, fan-out). Split into a cache short-circuit, a deterministic short-circuit, and a small `_general_conversation_event`. *(risk: low)*
- The 12-key `{"type":"final", ...}` result dict is hand-written 6× (659, 729, 775, 854, 896, 1110); `_default_route_fields` only abstracts 4 of 12 keys. Introduce one `_final_event(...)` builder. *(risk: low)*
- `adk.py:626-684` `_cached_response_event` reads every field with a `camelCase or snake_case` dual-key fallback (~7×). The cache is written by this same app in snake_case (`set_cached_chat_response`, 365); the camelCase halves are dead. *(risk: low — confirm no external cache writer)*

**Inline single-call privates** (each adds a name without adding clarity)
- `_get_or_create_session` (535, 1 call @1007) → INLINE
- `_classify_intent` (609, 1 call @1027; trivial `.value` coercion) → INLINE
- `_response_cache_lookup` (909, 1 call @1009) → INLINE (lean)
- `_unsupported_order_status_event` (874, 1 call) → INLINE once `_final_event` exists (it is boilerplate around one constant apology string)
- `_adk_telemetry.py::_named_sql_text` (18, 1 call @47) → INLINE
- `_adk_telemetry.py::_product_lookup_ran` (86, 1 call) → INLINE into `_effective_intent`

**Keep (earn their name):** `_make_tool_factories` (closure-bound tools, heavily tested — core ADK pattern), `_build_workflow` (test seam), `_append_display_history` (6 callers), `_deterministic_route_event` (genuine dispatch table), `_product_rag_event` / `_store_location_event` / `_product_availability_event` (substantial distinct routes).

**Structure:** the `_adk_history.py` (50 LOC) and `_adk_telemetry.py` (99 LOC) modules are small enough that folding them back into `adk.py` (or a single `_adk_support.py`) reduces cross-file jumping for low-Python readers. `_adk_grounding.py` is the one split that earns its keep.

**Fluff comments / legacy in this slice**
- `workflow.py:41-44` `if hasattr(agent, "model_copy")` — compat shim for older ADK agent types. Per the no-shim rule, keep only the real path (`LlmAgent.model_copy` exists). *(risk: low — pin installed ADK)*
- `_adk_grounding.py:165` 40-word inline stop-word regex and `:341` `ans[:-1] + "…"` slice trick — least-readable lines in the slice; re-shape into named pieces.
- `schemas/_chat.py:10-27` `ChatConversationCreate`/`ChatConversation` — suspected pre-ADK persistence leftovers; grep before deleting. *(risk: low)*

### WS2 — Products / System / Web domains

**Dead code (0 production callers; verified)**
- `products/services/services.py:111-130` `find_stores_by_city`, `find_stores_by_state`, `search_stores_by_zip` (the chat path uses `find_stores_by_location`). Delete methods + their named-SQL siblings.
- `products/services/services.py:197-202` `get_store_inventory`.
- `products/services/_location.py:54-55` `location_hint_matches` (just re-wraps `store_matches_hint`; 0 refs anywhere).
- `system/services/services.py:141-154` `delete_expired_responses` (CLI uses `invalidate_cache`).
- `system/schemas/_session.py` (whole file: `UserSessionCreate`, `UserSession`, `HistoryMeta`) — re-exported only, never constructed/mapped. (Live session = Litestar/SQLSpec plugin + `app_session` table; live history returns `ChatMessage`.) **KEEP `_cache.py::EmbeddingCache`** — the embedding-cache feature is live; the struct is wired (typed) in Ch8, not deleted. `ResponseCache` stays.
- `products/services/maps.py` — `build_store_search_url` / `build_store_directions_url` are orphaned, but **the Maps feature is already live** via a *duplicate* inline builder in `_adk_grounding.py` (`_maps_search_url` @186, `_store_query_parts`, `_build_map_actions` @192) that attaches `map_actions` to store rows; `main.js:694-754` renders them as "Open in Google Maps" links. **Resolved (Decision 2): consolidate to `maps.py` as the single builder; delete the grounding duplicate.** Do **not** delete `maps.py`. *(risk: low)*

**Simplify**
- `products/services/services.py:284-289` — `config_kwargs` dict built to splat one key; inline `EmbedContentConfig(output_dimensionality=self.embedding_dimensions)`.
- `_vector.py:122-128` nested ternary for `performance_level` → explicit if/elif/else (low-Python readability).
- `_vector.py:69-91` HTMX-vs-JSON 503 dual branch repeated 3× → extract a 503-response builder.
- `_vector_helpers.py:20-43` two near-identical marker lists → merge.
- `_metrics.py:25-31` `calculate_trend` defined in handler, called once → inline.

**Fluff docstrings:** `_products.py:17,33,53,69` docstrings restate the class name ("Product entity from database.") — drop or make behavior-bearing.

**Keep:** `parse_plan_rows` (38-line DBMS_XPLAN parser — isolating it *helps* the Oracle-literate reader), `_rank_availability` (2 callers, real dedup). `system/services.py` has no private methods.

### WS3 — Infra: settings, config, lib, server, cli, utils

> **Decision 5 — settings work routes through the existing PRD.** `.agents/specs/settings-config-consolidation_20260501/prd.md` is a thorough, review-gated, never-implemented plan that already identifies the exact dead knobs below *and* a fuller immutability/`ChatSettings` refactor (6 chapters). **Consolidate, don't duplicate:** reactivate that PRD as the canonical home for all `settings.py`/`config.py`/`plugins.py` work; this WS3 contributes only the *non-settings* dead-code deletions. One deviation to confirm: that PRD's lower-case field rename is broad churn with marginal readability benefit for this audience — recommend keeping its dead-knob deletion + immutability + quiet-factory goals but treating the rename as optional/low-priority.

**Dead settings knobs (delete; verified 0 readers — execute via the settings PRD)**
- Whole dataclasses: `ServerSettings` (`settings.py:200-221` + `Settings.server` @462), `AgentSettings` (385-403 + @465), `CacheSettings` (405-415 + @466). The server reads `LITESTAR_*` env via Granian, not `ServerSettings`.
- `VertexAISettings` knobs: `CACHE_TTL_SECONDS`, `CACHE_PREFIX`, `STREAM_BUFFER_SIZE`, `STREAM_TIMEOUT_SECONDS` (370-382).
- `DatabaseSettings`: `POOL_TIMEOUT` (77), `POOL_RECYCLE` (79), `ECHO` (81) — never placed in any config dict.
- `LogSettings.HTTP_EVENT` (234).
- **Keep:** `MapsSettings` (wired in `lib/log/_security.py:19-21`).

**Dead files / classes**
- `utils/sync_tools.py` (whole file — 0 importers).
- `lib/exceptions.py::ApplicationError` (0 references; docstring even names a foreign `AdvancedAlchemyException`).
- `lib/schema.py`: `CamelizedBaseSchema`, `BaseSchema`, `camel_case`, `BaseStruct.to_dict`, `Message` + the pydantic import they require (0 uses; only `CamelizedBaseStruct` survives).
- `utils/domains.py`: the entire listener-discovery subsystem (71-79, 115-131, 327-350, config knobs @46/148-149, `_DiscoveryState.listener_count`/`logged_listeners`) — no domain ships `events.py`/`listeners.py`.
- `server/plugins.py:42-47` stub `_SQLSpecPlugin` (the real subclass is defined inside `_initialize` @79).
- `lib/di.py:9,29` `Scope` re-export (consumers import `Scope` from `dishka` directly).

**Simplify (readability tax for low-Python readers)**
- `config.py` + `server/plugins.py` PEP-562 `__getattr__` lazy-init + duplicated `_reset()` machinery — consider explicit `init()`/eager build; at minimum the two `_reset()` are test-only plumbing. *(risk: med — touches fixtures + import timing)*
- `config.py:137` re-imports `cast` though already imported at module top (26).
- `utils/serialization.py:42-70` numbered banner comments restating `isinstance` checks → remove.
- `lib/log/_processors.py:71-137` defensive `try/except ImportError → []` though `structlog` is a hard dependency → drop.
- `cli/commands.py` inline-once delegators (`_show_model_info` @111, `_clear_application_cache` @42, `_upgrade_database` @87) and pointless rename `original_command = litestar_run_command` (69).
- `db/utils.py:46-71,90` comments restating SQL.

### WS4 — Documentation accuracy (the "100% accurate" mandate)

Because `CLAUDE.md` is a **symlink to `AGENTS.md`**, fix `AGENTS.md` once.

**High severity**
- `AGENTS.md:161-163` (≡ CLAUDE.md): replace the `task_type="RETRIEVAL_QUERY/DOCUMENT"` instruction with the real pattern — `embedding_purpose="query"/"document"` + `EMBEDDING_PURPOSE_INSTRUCTIONS` text prefix (`services.py:36-45,276-304`). This file directs agents, so the error is self-propagating.
- `AGENTS.md:20-22,177-179` + `project-guide.md:53-80` + `architecture.md:164-182`: Store/Inventory/Maps are described as "Planned"; they are **implemented** (`StoreService`, `stores.sql`, `inventory.sql`, ADK `STORE_LOCATION`/`PRODUCT_AVAILABILITY` routes, `store_product_inventory` fixture). Rewrite as shipped.

**Medium**
- Model name `gemini-embedding-2` → `gemini-embedding-2-preview` everywhere: `AGENTS.md:17,163`, `README.md:37`, `docs/index.md:31`, `docs/tour.md:78,97`, `docs/concepts/vector-search.md:19`, `.agents/patterns.md:29,119`, `project-guide.md:106`, `architecture.md:197`, `oracle-vector-search.md` (6 lines).
- Fixture counts → 130 products / 17 stores: `README.md:37`, `docs/concepts/vector-search.md:70`, `docs/reference/internals.md:98`.
- `docs/tour.md:95` references a non-existent `ProductService.embed_text`; embedding lives on `VertexAIService.get_text_embedding` (`services.py:272`).
- `.agents/tech-stack.md:10` "Google ADK 2.2.0" → pyproject pins `google-adk>=2.0.0b1`.
- `adk-agent-patterns.md:180-185` intent-label list is missing `PRODUCT_AVAILABILITY` (`classifier.py:17-24`).

**Low**
- `AGENTS.md:130` / `api.md:22` code blocks show `SQLSpecAsyncService[OracleAsyncDriver]` base; actual base is `OracleAsyncService` (`service.py:35`).
- `quickstart.md:48-49` attributes the 512M default to `configure_vector_memory.sql` (which sets 4G); the default is `database.py::DEFAULT_VECTOR_MEMORY_SIZE`.
- `tech-stack.md:8` conflates the `litestar-granian` plugin with the Granian server.

**`ADK2.md` is a migration *plan*, not a description** — its forward-looking sections must NOT be "corrected" to match current code. But flag two internal contradictions for whoever executes it: it specifies `gemini-embedding-002`/1536-dim and `RETRIEVAL_DOCUMENT/QUERY` for ADK memory, both inconsistent with the app's 3072-dim `embedding_purpose` stack.

**Clean (verified, no changes):** `docs/maps.md`, `docs/concepts/agent-flow.md`, `docs/concepts/rag.md`, `docs/reference/cli.md`, `docs/reference/developers.md`, `CONTRIBUTING.md`, `.agents/index.md`.

**`docs/_build/html/` — no action.** Gitignored, 0 tracked files. The stale `_modules/*.html` source snapshots exist only as a local untracked artifact and cannot enter version control; `make docs-clean` removes them if desired.

### WS5 — Frontend (templates + `src/resources/`)

**Layout map:** templates in `src/app/domain/web/templates/`; hand-written JS/CSS in `src/resources/` (`main.js` 1011 LOC, `vector-calculator.js`, `styles.css`, `vite.config.ts`); build output (do-not-edit) in `static/assets/main-*.js` + `styles-*.css`.

**Dead code (the non-stream chat path) — Resolved (Decision 1): delete the whole `/api/chat` route**
- `chat/controllers/_chat.py:63-167` `POST /api/chat` (both HTMX and JSON branches) is unreachable from the UI: the form posts only to `/api/chat/stream` (`chat.html.j2:73`), and `main.js` posts only to `/api/chat/stream` + `/session/clear`. Corroborated by `.agents/specs/ui-quality-fixes/spec.md:21`. It appears in `openapi.json` only as generated route surface, with no found consumer.
- **Deletion cascade:** also retire `ADKRunner.process_request` (`adk.py:1123` — no other app caller), the `CoffeeChatReply` schema (`_chat.py:38`), and the `metrics_badges` helper (`_helpers.py:37`). Delete partials `_chat_response.html.j2`, `_metrics_badges.html.j2`, `chat_error.html.j2`, and the metrics footer in `message.html.j2:18-63` (keep the partial — it renders page-load history).
- **Keep:** `validate_message` / `validate_persona` / `chat_form_from_request` / `location_context_from_form` (used by the stream handler) and the `ChatMessage` schema (used by history in `_adk_history.py` + `adk.py::get_history`). *(risk: med — the 3 test files calling `process_request` must be updated/removed)*

**Simplify / duplication**
- Welcome markup duplicated in `pages/chat.html.j2:56-67` and `main.js:56-67` (`welcomeMessageHtml`) → single source of truth.
- EXPLAIN PLAN table implemented twice — `main.js:179-241` (chat popover) and `partials/plan_lines.html.j2:18-59` (explore page). Both used; flag as the biggest low-JS maintenance hazard.
- `main.js` (1011 LOC) does 6 unrelated jobs (chat SSE, telemetry popover, charts, persona picker, geolocation, calculator) → split into `chat-stream.js` / `telemetry.js` / `charts.js` / `geolocation.js` + thin bootstrap.
- `explore.html.j2:121-144` six near-identical preset buttons (Gemini 3072 ≡ OpenAI 3072) → Jinja `{% for %}`; `:122` class conflict `text-xs ... text-base`; `:113-114` empty flex wrapper.

### WS6 — Test simplification (readability, not re-platforming)

> **Decision 4 — infra stays as designed.** Integration tests run against the repo-managed Oracle container (`tools/` + `make start-infra`) with data-level isolation: `integration/conftest.py` does migrate → idempotent `CREATE TABLE` bootstrap → `TRUNCATE` fixture tables → reload `.json.gz` → seed `SEED-SKU-001`, once per xdist worker, pinned to one worker group. The project **intentionally does not use pytest-databases**. Do **not** re-platform. WS6 is purely test-readability. *(Corrects an earlier draft recommendation.)*

**Legacy / deletion-guard tests**
- `tools/lib/utils.py:281-340` `migrate_sqlcl_connection` (+ caller branch 364-368) — `mcp_demo`→`cymbal_coffee` compat shim, 0 test refs. Delete.
- `test_adk.py:1067-1075` `test_module_level_tool_functions_are_deleted` — a "removed code stays removed" guard; delete.
- `test_vector.py:107,167` / integration `test_vector_search.py:89,92` `not hasattr(row, "distance")` guards — fold into one positive schema assertion.

**`test_adk.py` (1075 LOC) simplification**
- Drop tests pinning private surface: `_session_service`/`_classifier`/`_persona_manager` attrs (29-52), `_make_tool_factories` closure `__name__` asserts (55-264), `_build_workflow` kwargs capture (288-323), `_append_display_history` AttributeError (662-679).
- Extract a shared `make_runner(...)` / `fake_events(...)` helper (the same MagicMock graph is rebuilt at 366-465, 723-855, 923-1010 ≈ 300 LOC).
- Fix docstring "Phase 4 surface" (4) — spec-phase reference violates the docstring rule.

**Style drift**
- `@pytest.mark.asyncio` → `@pytest.mark.anyio` in `test_fixtures.py:34`, `test_classifier.py:32,47,78`, `test_workflow.py:68`.
- `.fn` route-handler unwrapping (`Controller.handler.fn(object.__new__(Controller), ...)`) in `test_metrics_charts.py`, `test_metrics_summary_cards.py`, `test_vector.py:149`, `test_explain_plan.py` → instantiate controllers normally or use `AsyncTestClient`.

---

## Library Documentation (ground-truth anchors for the rewrite)

| Component | Version / fact | Source |
|-----------|----------------|--------|
| Embedding model | `gemini-embedding-2-preview`, 3072 dims, `VECTOR(3072, FLOAT32)` | `settings.py:349`, `services.py:35` |
| Embedding API usage | `embedding_purpose` + `EMBEDDING_PURPOSE_INSTRUCTIONS` text prefix — **no `task_type`** | `services.py:36-45,276-304` |
| Google ADK | `>=2.0.0b1`; `LlmAgent` has `model_copy`; state via stock `OracleAsyncADKStore` + `SQLSpecSessionService` | `pyproject.toml`, `workflow.py:41`, `adk.py:577` |
| Chat / intent | Gemini Flash-Lite (`gemini-2.5-flash-lite`); `IntentLabel` = PRODUCT_RAG, GENERAL_CONVERSATION, STORE_LOCATION, PRODUCT_AVAILABILITY, ORDER_STATUS | `classifier.py:17-24` |
| DI | Dishka, 3 providers, handler-arg injection; `ioc.py` must not use `from __future__ import annotations` | `ioc.py` |
| Server | Granian via `coffee run`; reads `LITESTAR_*` env | `settings.py:208` |
| msgspec | bare-entity-noun Structs on `CamelizedBaseStruct` (37 subclasses) | `lib/schema.py` |

---

## Prior Art (internal)

- `.agents/specs/settings-config-consolidation_20260501/` — a thorough review-gated, never-implemented PRD that already scopes the settings dead-knob deletion (and more). **Decision 5: consolidate into it** rather than duplicate in a new spec.
- `.agents/specs/ui-quality-fixes/spec.md:21` and `.agents/research/research_adb_hooks_ux_lab/` — already identify the dead `/api/chat` HTML path (WS5).
- `.agents/plans/htmx-retirement_20260226.md` — context for why HTMX-swap partials are now dead; supports WS5 deletions.
- `.agents/knowledge/test-suite-reorganization_20260501.md` — prior test-layout work; WS6 builds on it.
- Memory `feedback_no_legacy_shims`, `feedback_test_isolation`, `feedback_docstrings` — directly govern WS1/WS3/WS6 acceptance.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Deleting `/api/chat` breaks an undocumented external consumer | Low | Med | Decision is to delete (no consumer found; only generated `openapi.json` surface). Run one final repo-wide grep for `/api/chat"` posts before removal. |
| Removing PRODUCT_RAG re-ground branch changes streaming output | Low | Med | Add an integration test asserting PRODUCT_RAG output is byte-identical before/after; verify classifier vs `_effective_intent` can't diverge. |
| Inlining/merging `_adk_*` modules breaks the test seams (`_make_tool_factories`, `_build_workflow`) | Med | Med | Keep those two privates; only inline the genuinely single-call ones. Run `test_adk.py` after each inline. |
| `make_coffee_node` shim removal breaks on an older installed ADK | Low | Low | Pin/verify installed `google-adk` exposes `LlmAgent.model_copy` (it does at `>=2.0.0b1`). |
| Pruning `test_adk.py` private-surface tests drops real coverage | Med | Med | Replace each deleted private-surface assertion with a public-behavior test (via `stream_request` or `AsyncTestClient`); keep the `_make_tool_factories`/`_build_workflow` seams. |
| Maps consolidation changes rendered `map_actions` shape | Low | Low | `maps.py` builder must emit the same `{type,label,url}` shape grounding produces today; cover with the existing `test_maps.py` + a grounding `map_actions` assertion. |
| Doc edits introduce *new* inaccuracies | Med | High | Every edited claim must be grep-verified against source (the `docs/_build` self-correction is the cautionary example). Add a doc-lint pass. |
| Deleting "dead" code that a planned feature needs (e.g. `maps.py`) | Low | Med | `maps.py` is the one judgment call — decide wire-vs-delete with the user, don't auto-delete. |

**Recovery strategy.** Each workstream is an independent, revertable commit/flow. Checkpoints: (1) after dead-code deletion (mechanical, `make lint && make test` must stay green), (2) after `adk.py` refactor (full chat integration test), (3) after doc rewrite (manual diff review), (4) after test re-platform (CI green twice). Rollback = revert the workstream commit; no cross-workstream coupling except WS6 tests must follow WS1–WS3 deletions.

---

## Recommended Approach

Sequence by **risk-ascending, leverage-descending**, so the safest high-value wins land first and de-risk the rest:

1. **WS4 — Docs accuracy** (no code risk; fixes the agent-misdirecting `task_type` error first so subsequent agent-assisted work is grounded). Edit `AGENTS.md` once (symlink covers CLAUDE.md).
2. **WS3 + WS2 dead-code deletion** (mechanical, verified 0-caller): `sync_tools.py`, `lib/exceptions.py`, pydantic `schema.py` half, `domains.py` listener subsystem, `plugins.py` stub, dead store methods, dead schemas. **Settings deletions route through the existing `settings-config-consolidation_20260501` PRD** (Decision 5), not a new spec. Gate: `make lint && make test` green.
3. **WS1 — `adk.py`**: delete `record_search_metric`, remove the duplicated PRODUCT_RAG branch, introduce `_final_event`, inline the single-call privates, fold `_adk_history`/`_adk_telemetry`. Gate: chat integration test.
4. **WS5 — Frontend**: delete the `/api/chat` route + cascade (Decision 1) + dead partials, dedupe welcome/EXPLAIN-PLAN, split `main.js`. Fold the maps consolidation (Decision 2) in here or alongside WS1.
5. **WS6 — Tests**: delete deletion-guard + private-surface tests, normalize `@pytest.mark.asyncio`→`anyio`, extract `test_adk.py` mock helpers, delete `migrate_sqlcl_connection` + its tests. (Infra unchanged — no re-platform.)
6. **Comment/fluff sweep** folded into each workstream's edits (don't do a separate pass — clean comments as you touch each file).

This maps to ~5 child flows under one PRD. WS2/WS3 deletions can run in parallel; WS6 must follow WS1–WS3.

---

## Resolved Decisions (2026-06-14)

All five open questions are resolved (user direction + code review). These are now binding inputs to the PRD.

1. **`/api/chat` → delete the whole route, keep only `/api/chat/stream`.** The app does not stream-and-non-stream two ways; the non-stream route is unreached by the UI. Cascade-delete `process_request`, `CoffeeChatReply`, `metrics_badges`, and the 3 dead partials; update the 3 tests that call `process_request`. Keep the shared validators + `ChatMessage`. *(One route, not two.)*
2. **Maps → consolidate into one builder; wire `maps.py` in.** The feature is already live through a *duplicate* inline builder in `_adk_grounding.py`. Make `products/services/maps.py` the single no-key Maps URL source, call it from `_build_map_actions`, and delete grounding's `_maps_search_url` + `_store_query_parts`. `maps.py` becomes live (not deleted). Sub-choice for the plan: also emit a `directions` action (makes `build_store_directions_url` live and matches the classifier's advertised "directions" capability) **or** drop `build_store_directions_url` to avoid leaving it dead — recommend emitting directions since the frontend renderer is generic.
3. **`_adk_*` modules → fold to reduce file/module bloat.** Merge `_adk_history` (50 LOC) and `_adk_telemetry` (99 LOC) back into `adk.py` (or a single `_adk_support.py`); keep `_adk_grounding` separate (it earns its split). Fewer cross-file jumps for low-Python readers.
4. **Test infra → unchanged.** The project deliberately uses its own `tools/`-managed Oracle container with data-level isolation, **not** pytest-databases. No re-platform. WS6 is test-readability only. *(Corrects the earlier draft; memory `feedback_test_isolation` updated to match.)*
5. **Settings → consolidate into the existing PRD.** `settings-config-consolidation_20260501` is more complete than a fresh WS3 settings spec; reactivate it as the canonical settings home and reference it from the new roadmap. Deviation to confirm: treat its lower-case field rename as optional (marginal readability benefit, broad churn) while keeping its dead-knob deletion + immutability + quiet-factory goals.

### Remaining micro-decision for the plan (non-blocking)
- Whether to render a second `directions` map action (Decision 2 sub-choice). Default: yes.

---

## Research Outputs

**This research informs:**
- PRD: `.agents/specs/<prd_id>/prd.md` (when created) — suggested: `demo-simplification`
- Child flows: `docs-accuracy`, `deadcode-sweep`, `adk-readability`, `frontend-deadpath`, `test-overhaul`

**Next step:** Run `/flow:flow-prd` to turn these six workstreams into a Master Roadmap, or `/flow:flow-plan` to plan a single workstream (recommend starting with **WS4 — Docs accuracy** as the zero-risk, agent-grounding first move).

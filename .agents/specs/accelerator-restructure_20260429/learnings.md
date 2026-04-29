# Learnings: accelerator-restructure_20260429

> Notes captured during implementation. Synced from Beads task notes via `/flow:sync`.

## Pre-implementation findings (planning phase, 2026-04-29)

- Accelerator's `lib/service.py` is a **pure re-export facade** — there is no custom subclass. The codebase delegates everything to sqlspec's `SQLSpecAsyncService`. Mimic that exactly.
- Accelerator uses **5 providers** but the count is misleading: 3 of them (`LitestarPersistenceProvider`, `CliPersistenceProvider`, `WorkerPersistenceProvider`) are scope-specific copies of the same driver-providing logic. We only need the Litestar variant for now; CLI and Worker can be added if/when SAQ lands.
- The `current_price`/`price` mismatch at `services.py:47` has a band-aid mapping at line 119 that has been silently degrading vector-search response shape since the column was renamed. Reviewers missed it because the band-aid remapped onto the `distance` field — type checker happy, semantics wrong.
- Filter dependencies are **purely additive** to the controller `dependencies` dict — no risk of clobbering hand-rolled deps if the rewrite is methodical.

## Ch 2.1 — Service base + facade (closed `[aad45ae]`, 2026-04-29)

- `lib/service.py` rewritten as a thin re-export of sqlspec primitives (`SQLSpecAsyncService`, filter types, `apply_filter`, `create_filter_dependencies`). Removed the local Generic[AsyncDriverT] wrapper.
- `sed -i 's/SQLSpecService/SQLSpecAsyncService/g'` across `src/py/app/` was clean — no `__init__` overrides depended on the wrapper. 7 domain service classes now inherit directly from sqlspec.

## Ch 2.2 — Named SQL extraction (closed `[c9a44a1]`, 2026-04-29)

- Refactored from 30 candidate keys down to **10 reusable named queries** by adopting `sqlspec.sql.{insert,update,delete}` AST builders for trivial CRUD. The general rule: only stash a query in `db/sql/*.sql` when it benefits from `.where(...)` chaining or has non-trivial SELECT shape.
- `db_manager.get_sql("...").where("predicate")` returns a chainable query object. Single-column-WHERE variants (`find_stores_by_city`, `_state`, `_id`) collapse to one base query + `.where(...)` calls — saved 5 keys.
- Driver call sites must use **kwargs binds** (`select_one_or_none(query, id=product_id, schema_type=Product)`), not dict binds. The driver expects keyword arguments in sqlspec 0.46.
- Always pass `schema_type=` so the driver returns typed structs directly — no manual `Schema(**row)` wrap needed.
- `SQLSpecAsyncService.paginate(query, *filters, schema_type=T)` replaces hand-rolled count+select pairs. Drops 2 separate named queries (`count-products`, `count-exemplars`).
- Hyphen vs underscore: sqlspec's registry stores keys with underscore but `get_sql("hyphen-name")` works because the loader normalizes. Test regex must require **whitespace lookahead** (`(?=[ \t\n])`) after `SELECT/UPDATE/...` to avoid false positives on hyphenated query keys like `"update-product-embedding"`.
- CLI `force=True` branch was hiding inline SQL (`SELECT id, name, description, embedding FROM product`). Eliminated by extending `ProductService.get_products_for_embedding(force=)` to mirror `ExemplarService.get_exemplars_without_embeddings`.

## Ch 2.3 — 3-provider Dishka collapse (closed `[e49131f]`, 2026-04-29)

- `IntegrationsProvider` holds **only** the truly APP-scoped externals: `genai.Client`, `OracleAsyncADKStore`, `SQLSpecSessionService`, `ADKRunner`. `VertexAIService` and `OracleVectorSearchService` were proposed APP-scoped in the spec but stay **REQUEST-scoped** in `DomainServiceProvider` because `VertexAIService` captures a REQUEST-scoped `CacheService` reference at construction time — promoting it to APP would pin a stale per-request reference. Spec text refined accordingly.
- `provide_intent_classifier` slot deferred: YAGNI wins until Ch 3 actually lands `FlashLiteIntentClassifier`. Reserving an empty provider method now would be dead code.
- `ADKRunner(session_service)` signature unchanged. The spec mentioned `(session_service, classifier, persona_manager)` but `PersonaManager` is a static class today (`PersonaManager.get_system_prompt(...)` is called as a class method), not an injected instance. No Ch 3 wiring change is required here.
- Dishka `AsyncContainer` exposes no public provider list; introspection requires walking `container.registry.child_registry` chain (one registry per scope). For test stability, the implementation also exposes a `PROVIDERS: tuple[type[Provider], ...]` module-level constant — tests assert against this rather than a private API.
- Lint trap: this module **must not** carry `from __future__ import annotations`. Dishka uses `get_type_hints()` at provider-init time, which under PEP 563 sees string forward refs and fails. Encoded as a guard test (`test_ioc_module_does_not_use_future_annotations`).
- Existing `test_chat_di.py` monkeypatched `ChatServiceProvider.get_*` methods. After the collapse those methods live on `IntegrationsProvider`. Test rewritten one-to-one — same DI semantics, different host class.

## CLI flatten + accelerator manage.py (parallel work, 2026-04-29)

- Application CLI command renamed from `app` to `coffee` (`[project.scripts] coffee = "app.__main__:run_cli"`). All Makefile + README + CLAUDE.md references migrated.
- `[tool.sqlspec] config = "app.config.db"` added to pyproject so the standalone `sqlspec` CLI auto-discovers the config (matches accelerator). The custom `manage.py database` group still pre-injects `ctx.obj["configs"]` directly — the pyproject entry is a fallback for direct `sqlspec` invocations.
- `manage.py` now mirrors dma/accelerator: 6 top-level groups (`init`, `install`, `doctor`, `infra`, `database`, `assets`). Container ops are flat (`infra start/stop/restart/status/logs/wipe`) — the `-local-container` suffix die. `wallet` and `connect` bundle under `database` so DB-related concerns cluster.
- Application CLI flattens too: `coffee upgrade/downgrade/load-fixtures/export-fixtures/bulk-embed/clear-cache/model-info` are top-level. The sqlspec auto-mounted `db | database` group is suppressed via a `SQLSpecPlugin` subclass whose `on_cli_init` is a no-op (the upstream plugin auto-mounts; our `ApplicationCore` plugin runs first so `cli.commands.pop("db")` doesn't take — subclass override is the right hammer).
- `async_inject` decorator ported from accelerator to `src/py/app/cli/utils.py`. Each coffee command now declares its dependencies as type-annotated kwargs (`product_service: ProductService`, etc.); the decorator builds a fresh REQUEST-scoped Dishka container, resolves the deps, sets `worker_container_var` and `request_container_var`, and runs the coroutine via `sqlspec.utils.sync_tools.run_`. Eliminates the manual `db_manager.provide_session(db) as session: ProductService(session); CacheService(session); ...` boilerplate per command.
- Trap: with `from __future__ import annotations`, `get_type_hints()` evaluates string annotations against module globals — so the service classes used as deps **must be imported at runtime** (not under `TYPE_CHECKING`). Marked with `# noqa: TC001` so ruff doesn't push them back into the type-checking block.

## Ch 2.4 — Filter dependencies + paginated handlers (closed `[4167a45]`, 2026-04-29)

- `create_filter_dependencies({...})` emits the dep keys `{filters, limit_offset_filter, search_filter, id_filter, order_by_filter, created_filter}` — the *configuration* keys (`pagination_type`, `sort_field`, `id_field`, `search`, `created_at`) are **input shape**, not output shape. Tests assert against the actual emitted keys. No rename shims (per user direction): the tests adapt to sqlspec's vocabulary, not the other way around.
- `B008` is now globally ignored (`pyproject.toml`). The Litestar idiom `filters: list[FilterTypes] = Dependency(skip_validation=True)` is a function call in a default-value slot — flake8-bugbear's general rule against this is wrong for Litestar's design; accelerator ignores B008 for the same reason.
- New schema gotcha (cousin of the Dishka PEP 563 trap): handler-visible msgspec structs with `from __future__ import annotations` AND `if TYPE_CHECKING: from datetime import datetime` break Litestar's OpenAPI generator at boot. Litestar calls `get_type_hints()` to materialize response models — string forward refs fail because `datetime` isn't in module globals. Fix: import `datetime` at runtime with `# noqa: TC003`. This bit `Product`/`Store` (already shipped, just newly exposed via handlers) and the new `IntentExemplar`. Worth promoting to a top-level patterns.md note in Ch 2.7.
- `list-products` was added as a new named query specifically for list endpoints. The existing `get-product` projects `embedding` (3072 dims) — heavy for list responses. `list-products` projects everything **except** embedding. Same logic applied to widening `list-exemplars`. Pattern: keep one-row queries fat, list queries lean.
- `paginate(query, *filters, schema_type=T)` does the count+select+ordering+offset internally — services collapse to a one-liner. Tests assert the return-type annotation is `OffsetPagination[T]` via `typing.get_origin`/`get_args` so the contract is type-checked at unit level (no DB needed).
- Phase 4.4 was a no-op confirmation: a thorough `grep -rn -E "(query_param|request\.url\.query|Parameter.*limit|Parameter.*offset|skip\s*=|page_size)" src/py/app/domain/ src/py/app/server/` returned zero hits. The codebase had no hand-rolled pagination to remove.
- Domain layout: kept `controllers.py` flat in this chapter even though the spec sample shows `controllers/_product.py`. The DomainPlugin auto-discovers both flat files and packages, so adding ProductController/StoreController/ExemplarController to existing flat files keeps the diff scoped. Phase 5 normalizes the layout to packages — that's the right place for the structural churn.

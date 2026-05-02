# Flow: Domain-Service Restructure (domain-service-restructure_20260429)

*Chapter 2 of [cymbal-coffee-reset_20260429](../cymbal-coffee-reset_20260429/prd.md)*
*Beads epic: `oracledb-vertexai-4d6.2` (blocked by Ch 1, blocks Ch 3 and Ch 4)*

---

## Specification

> Current-state sync (2026-05-02): this completed chapter was written before the
> source-tree flatten. Treat `src/py/app`, `src/py/tests`, and `uv run app ...`
> references below as historical evidence unless the line is explicitly updated.
> Current code lives under `src/app` and `src/tests`; run the server with
> `uv run coffee run`; end users bootstrap with `uv run coffee upgrade`; raw
> SQLSpec developer commands stay under `uv run python manage.py database ...`.

### Objective

Reshape `src/app/` to the domain-service structural pattern — **without** removing Dishka. After this chapter every domain follows the same shape: `controllers/` → `services/` (subclassing `SQLSpecAsyncService`) → `db/sql/{domain}.sql` named queries → `schemas/` DTOs. All inline SQL is eliminated. The 4 scattered Dishka providers collapse to **exactly three providers**: `LitestarPersistenceProvider`, `IntegrationsProvider` (APP-singletons: Vertex client, ADKRunner, OracleAsyncADKStore, SQLSpecSessionService, FlashLiteIntentClassifier), and `DomainServiceProvider` (REQUEST-scoped domain services). List endpoints adopt `create_filter_dependencies()` so paginated responses stop being hand-rolled. The `current_price`/`price` schema-vs-query bug is fixed at the source.

### Code Analysis Summary (verified 2026-04-29)

**Reference pattern:**

- `app/lib/service.py` is a pure facade re-exporting `SQLSpecAsyncService`, `SQLSpecSyncService`, `LimitOffsetFilter`, `OffsetPagination`, `PaginationFilter`, `apply_filter`, and `create_filter_dependencies` from sqlspec. **Not a custom subclass** — inheritance chain stops at sqlspec's base.
- Providers live in one composition module; a `make_litestar_container()` factory composes them.
- ASGI app construction uses `Litestar(plugins=[ApplicationCore()])` and then `setup_dishka(container, app)`.
- `ApplicationCore` implements `InitPluginProtocol` + `CLIPluginProtocol` and discovers controllers from each `app.domain.*.controllers` package.
- List controllers define a `create_filter_dependencies({...})` block as a `dependencies` class attr; handler signatures accept `filters: list[FilterTypes] = Dependency(skip_validation=True)`.
- Services call `await self.paginate(db_manager.get_sql("list-..."), *filters, schema_type=Schema)` and use `.where(...)` on named query objects for focused single-row reads.
- SQL files use `-- name: <key>` directives to register named queries; `db_manager.load_sql_files()` registers them at boot.

**Current oracledb-vertexai-demo state:**

- `src/py/app/lib/service.py:74-80` — has its own `SQLSpecService` wrapper (`Generic[AsyncDriverT]`) that does **not** inherit from sqlspec's `SQLSpecAsyncService`; misses `paginate`, `get_or_404`, `exists`, `begin_transaction`. Replace with the sqlspec-base re-export pattern.
- **4 Dishka providers, scattered:**
  1. `src/py/app/ioc.py:15-27` — `LitestarPersistenceProvider` (config @ APP, driver @ REQUEST).
  2. `src/py/app/domain/system/services/__init__.py:20-24` — `SystemServiceProvider` (Cache/Metrics/Exemplar @ REQUEST).
  3. `src/py/app/domain/chat/services/__init__.py` — `ChatServiceProvider` (Chat/ADK services).
  4. `src/py/app/domain/products/services/__init__.py:26-57` — `ProductsServiceProvider` (Product/Store/VertexAI/OracleVectorSearch @ REQUEST + Vertex client @ APP).
- **Inline SQL across 26+ sites:**
  - `src/py/app/domain/products/services/services.py:37,47,*` — vector search + product fetch.
  - `src/py/app/domain/system/services/services.py:137,153,157,160,163,169,173,182,186,190,219,229,242` — cache + metrics + exemplar queries.
  - `src/py/app/domain/chat/services/adk.py` — embedded SQL in IntentService/ExemplarService.
- **Zero `create_filter_dependencies()` callsites** — verified via `grep -rn "create_filter_dependencies" src/py/app/`. Controllers hand-roll limit/offset where pagination exists.
- **`current_price` bug:** `src/py/app/domain/products/services/services.py:47` queries `current_price` but the `product` DDL column is `price`. There is a band-aid mapping at line 119 (`"current_price"` key compared to `distance`). This silently degrades vector-search results and confuses every downstream consumer. Fix here, not in Ch 1.
- **No `ApplicationCore` plugin** — `src/py/app/server/core.py` exists but registers controllers explicitly rather than via package auto-discovery; collapse to the documented discovery pattern.
- **Domain folder layout inconsistency:** some domains use `controllers.py` (single file), others use `services.py` + `services/__init__.py`. Normalize to **`controllers/` package + `services/` package + `schemas/` package**.

### Requirements

1. `src/app/lib/service.py` is a re-export facade. Every existing service inherits from sqlspec's `SQLSpecAsyncService` (gains `paginate`, `get_or_404`, `exists`, `begin_transaction`).
2. Every inline SQL string in `src/app/domain/` is moved to `src/app/db/sql/{domain}.sql` with a `-- name: <key>` directive, registered by `db_manager.load_sql_files()` at boot, and accessed via `config.db_manager.get_sql("<key>")`.
3. The 4 Dishka providers collapse to **`DomainServiceProvider`** (REQUEST scope, all domain services) and **`LitestarPersistenceProvider`** (config @ APP, driver @ REQUEST). APP-singletons (`OracleAsyncADKStore`, `SQLSpecSessionService`, `ADKRunner`, `genai.Client`, `VertexAIService`) live as APP-scoped `@provide` methods on a third compact provider — `IntegrationsProvider` — so REQUEST-scoped services can depend on them via DI.
4. Every list/search controller adopts `create_filter_dependencies(...)` and accepts `filters: list[FilterTypes] = Dependency(skip_validation=True)`. Handler bodies become `return await service.list_with_count(*filters)` or equivalent.
5. `services.py:47` and the band-aid at `:119` are gone; the named SQL uses `price`; the response DTO uses `price`.
6. `ApplicationCore` plugin in `src/app/server/core.py` follows the documented pattern: `InitPluginProtocol` registers all controllers via package-level discovery. The old `coffee_demo_group` path is gone; `coffee` is the hand-rolled app CLI and raw developer commands live on `manage.py`.
7. Domain folder layout normalized — every domain has `controllers/`, `services/`, `schemas/` as packages (not single files).
8. `.agents/patterns.md` rewritten to reflect post-Ch 2 reality (named SQL pattern, `Inject[T]`, `create_filter_dependencies`, single-provider-per-app pattern).

### Acceptance Criteria

- `grep -rn "\"\"\"SELECT\\|\"\"\"INSERT\\|\"\"\"UPDATE\\|\"\"\"DELETE\\|\"\"\"MERGE" src/app/domain/` returns **zero** hits (no inline SQL in domain code).
- `grep -rn "current_price" src/app/` returns **zero** hits.
- `grep -rn "create_filter_dependencies" src/app/domain/` finds at least 3 callsites (products, stores, exemplars at minimum).
- `python -c "from app.ioc import make_litestar_container; c = make_litestar_container(); print(len(c._providers))"` reports exactly **3** providers (Litestar built-in not counted): `DomainServiceProvider`, `LitestarPersistenceProvider`, `IntegrationsProvider`.
- All existing tests pass; named-SQL loading tests verify every named-SQL key referenced by services exists in `src/app/db/sql/*.sql`.
- `make lint && make test` green.
- `uv run coffee run` boots; `POST /api/vector-demo` returns results with the correct `price` field; chat endpoint still answers.

### Risks / Known Gotchas

- **`SQLSpecAsyncService` constructor signature** in sqlspec 0.46 takes `driver` as the first positional arg. Existing service `__init__` overrides may break — audit each `class XService(SQLSpecService): def __init__(self, ...)` in the codebase and convert to the new base-compatible signature.
- **Dishka REQUEST-scoped factory must be `async def` returning `AsyncIterator[Driver]`** if it owns connection lifecycle. It should yield the request driver and own cleanup at request scope.
- `create_filter_dependencies()` adds keys to handler `dependencies` dict — ordering matters if a controller already declares its own `dependencies`. Merge, don't overwrite.
- Named-SQL files are loaded once at boot; **tests that mutate SQL files at runtime will not see updates** without `db_manager.reload_sql_files()`. Document in patterns.md.
- The current `lib/service.py` `SQLSpecService` is referenced from many call sites — refactor as a *renaming* (use `git mv` + sed across `src/py/app/`) to keep diffs reviewable.
- **`current_price` may be referenced from frontend types** (`src/js/src/lib/generated/schemas.ts`). Frontend deletion happens in Ch 4, so a stale generated type survives the gap. Acceptable — Ch 4 regenerates from updated OpenAPI.

---

## Implementation Plan

### Phase 1: Service base + facade (`oracledb-vertexai-4d6.2.1`)

- [x] **1.1** Rewrite `src/py/app/lib/service.py` as a re-export facade:
  ```python
  from sqlspec.service import SQLSpecAsyncService, SQLSpecSyncService
  from sqlspec.core.filters import (
      LimitOffsetFilter, OrderByFilter, SearchFilter, BeforeAfterFilter,
      InCollectionFilter, FilterTypes,
  )
  from sqlspec.extensions.litestar.providers import (
      OffsetPagination, PaginationFilter, apply_filter, create_filter_dependencies,
  )
  __all__ = [...]
  ```
  Delete the local `SQLSpecService` Generic wrapper.
- [x] **1.2** `grep -rln "from app.lib.service import SQLSpecService" src/py/app/ | xargs sed -i 's/SQLSpecService/SQLSpecAsyncService/g'`. Manually audit each file: ensure no `__init__` overrides, no Generic[AsyncDriverT] usage that's now dead.
- [x] **1.3** Add a unit test `src/py/tests/unit/test_service_base.py` that imports each domain service and asserts `issubclass(Cls, SQLSpecAsyncService)`.

### Phase 2: Named SQL extraction (`oracledb-vertexai-4d6.2.2`)

- [x] **2.1** Create `src/py/app/db/sql/products.sql`. Final keys: `get-product` (no WHERE; callers chain `.where(...)` for id/name lookups), `list-products-for-embedding` (no WHERE; force flag controls `.where("embedding IS NULL")` chain), `vector-search-products`. Trivial UPDATE/INSERT/DELETE replaced with `sqlspec.sql.{update,insert,delete}` AST builder, so `count-products-by-category` and `update-product-embedding` are NOT separate named queries.
- [x] **2.2** Create `src/py/app/db/sql/system.sql`. Final keys: `get-cached-response`, `get-cached-embedding`, `get-cache-stats`, `get-performance-stats`, `vector-search-exemplars`, `list-exemplars`. Cache/embedding mutations + `delete-*-all` + `record-search-metric` + `update-exemplar-embedding` use `sqlspec.sql.*` AST builder (no separate named queries needed).
- [x] **2.3** Skipped — `domain/chat/services/adk.py` has zero own SQL; IntentService and AgentToolsService delegate to ProductService/ExemplarService/MetricsService. ADK session storage stays inside `OracleAsyncADKStore` (sqlspec extension). No `db/sql/chat.sql` file was needed.
- [x] **2.4** Create `src/py/app/db/sql/stores.sql`. Single key `list-stores` (no WHERE); StoreService.{find_stores_by_city, find_stores_by_state, get_store_by_id} chain `.where(...)`.
- [x] **2.5** `src/py/app/config.py:58` already calls `db_manager.load_sql_files(BASE_DIR / "db" / "sql")` after `add_config(db)`. Verified at runtime — 10 keys register on import.
- [x] **2.6a** ProductService methods use `db_manager.get_sql("<key>").where(...)` with kwargs binds + `schema_type=Product`. `update_embedding` uses `sql.update("product").set(...).where_eq("id", ...)`.
- [x] **2.6b** CacheService, MetricsService, ExemplarService migrated. `record_search` uses `sql.insert("search_metric").values(**msgspec.to_builtins(...))`. `bump-embedding-cache-hit` uses `sql.update("embedding_cache").set(hit_count=sql.raw("hit_count + 1"), ...)`. CLI's force-mode inline `SELECT id, name, description, embedding FROM product` eliminated by extending `ProductService.get_products_for_embedding(force=)` to mirror `ExemplarService.get_exemplars_without_embeddings`.
- [x] **2.6c** No chat-side SQL to migrate.
- [x] **2.7** Added `src/py/tests/unit/test_named_sql_loading.py` (kept as **unit** test — no DB needed; regex-scrapes services for `get_sql("...")`, checks each key resolves via `db_manager.has_sql_query(...)`, verifies no inline SQL keywords remain in domain services). Lives in `tests/unit/` per the no-dev-container-coupling rule. 15 tests, all green.

### Phase 3: Provider collapse (`oracledb-vertexai-4d6.2.3`)

- [x] **3.1** Three providers landed in `src/py/app/ioc.py`. Refinement vs original spec: `VertexAIService` and `OracleVectorSearchService` stay REQUEST-scoped under `DomainServiceProvider` (VertexAIService captures CacheService, which is REQUEST-scoped — making it APP would pin a stale per-request reference). `provide_intent_classifier` slot deferred to Ch 3 per YAGNI (class doesn't exist yet); `ADKRunner(session_service)` signature unchanged because PersonaManager is a static class today.
- [x] **3.2** `make_litestar_container()` composes `LitestarProvider() + *(P() for P in PROVIDERS)`; `PROVIDERS` tuple exposed for introspection.
- [x] **3.3** Per-domain `services/__init__.py` files now re-export service classes only — Provider classes deleted.
- [x] **3.4** `src/py/app/server/asgi.py` was already calling `setup_dishka(make_litestar_container(), app)`; no change needed.
- [x] **3.5** `src/py/tests/unit/test_container_shape.py` — 8 tests asserting tuple shape, registry chain, factory scopes, no `from __future__ import annotations`. `test_chat_di.py` rewritten to monkeypatch `IntegrationsProvider` instead of the now-gone `ChatServiceProvider`.

### Phase 4: Filter dependencies + paginated handlers (`oracledb-vertexai-4d6.2.4`)

- [x] **4.1** `ProductController` landed in `src/py/app/domain/products/controllers.py` (still flat — Phase 5 normalizes to package layout). Wires `create_filter_dependencies({...})` exactly as spec'd; handler signature uses `Inject[ProductService]` + `filters: list[FilterTypes] = Dependency(skip_validation=True)`. Refinement: domain layout conversion deferred to Phase 5 to keep this chapter focused on the filter-dep pattern. `[4167a45]`
- [x] **4.2** `ProductService.list_with_count(*filters)` calls `self.paginate(db_manager.get_sql("list-products"), *filters, schema_type=Product)`. New named query `list-products` projects every column **except** `embedding` (3072-dim vector is too heavy for a list endpoint). `[4167a45]`
- [x] **4.3** `StoreController` (`/api/stores`) and `ExemplarController` (`/api/exemplars`) landed with the same filter-dep pattern. `IntentExemplar` schema added (`src/py/app/domain/system/schemas/_exemplar.py`); `list-exemplars` projection widened to all rows minus embedding. `[4167a45]`
- [x] **4.4** No-op confirmation: `grep` over `src/py/app/domain/` and `src/py/app/server/` finds **zero** hand-rolled `limit`/`offset`/`page_size` query-param parsing. `[4167a45]`

#### Ch 2.4 implementation notes (refinements vs spec)

- The dep-keys emitted by `create_filter_dependencies` are `{filters, limit_offset_filter, search_filter, id_filter, order_by_filter, created_filter}`. Tests assert against the actual emitted keys, not the renamed-for-prose versions in earlier spec drafts. Per user direction (2026-04-29), no rename shims were introduced.
- Lint pivot: `B008` ignored globally in `pyproject.toml`. The Litestar idiom `field = Dependency(...)` / `field = Parameter(...)` is a function call in a default-value slot and trips the rule, so the global ignore is the correct tool.
- Schema gotcha: handler-visible msgspec structs with `from __future__ import annotations` AND `if TYPE_CHECKING: from datetime import datetime` break Litestar's OpenAPI generator (`get_type_hints()` evaluates string annotations at runtime). Fix: import `datetime` at runtime (`# noqa: TC003`). Same family of gotcha as the `ioc.py` PEP 563 trap.

### Phase 5: ApplicationCore plugin + domain layout normalization (`oracledb-vertexai-4d6.2.5`)

- [x] **5.1** ApplicationCore stays as-is — `server/core.py` registers a `DomainPlugin` whose discovery walks `app.domain.*.controllers`. The literal pkgutil sample below would duplicate the plugin's discovery layer; refinement: keep the plugin layer and satisfy the spec's structural intent via the explicit `controllers: list[type[Controller]]` export contract added in 5.2.
  ```python
  # Earlier sample (NOT applied - the existing DomainPlugin discovery layer already owns this work):
  import importlib, pkgutil
  import app.domain
  class ApplicationCore(InitPluginProtocol, CLIPluginProtocol):
      def on_app_init(self, app_config: AppConfig) -> AppConfig:
          for _finder, name, _is_pkg in pkgutil.iter_modules(app.domain.__path__, prefix="app.domain."):
              try:
                  ctrl_pkg = importlib.import_module(f"{name}.controllers")
              except ModuleNotFoundError:
                  continue
              app_config.route_handlers.extend(getattr(ctrl_pkg, "controllers", []))
          return app_config
  ```
- [x] **5.2** Each domain normalized to **packages** for controllers/services/schemas (services and schemas were already packages):
  - `domain/chat/controllers/` → `_chat.py` (CoffeeChatController); `__init__.py` exports `controllers = [CoffeeChatController]`.
  - `domain/products/controllers/` → `_products.py` (Product/StoreController), `_vector.py` (VectorController); `__init__.py` exports `controllers = [ProductController, StoreController, VectorController]`.
  - `domain/system/controllers/` → `_exemplar.py` (ExemplarController), `_system.py` (SystemController), `_metrics.py` (MetricsController); `__init__.py` exports `controllers = [ExemplarController, MetricsController, SystemController]`.
  Each `__init__.py` re-exports classes via `__all__` AND publishes the explicit `controllers: list[type[Controller]]` contract — DomainPlugin's introspection still finds them, but the contract is now stable for any future inlining.
- [x] **5.3** Flat `domain/{chat,products,system}/controllers.py` files deleted after package conversion.

### Phase 6: `current_price` bug fix (`oracledb-vertexai-4d6.2.6`)

- [x] **6.1** In `src/py/app/db/sql/products.sql`, the `vector-search-products` query selects `price` (not `current_price`). [6cc3ca2] *(SQL half absorbed during Ch 2.2's named-SQL extraction; verified in 2.6.)*
- [x] **6.2** A typed `ProductMatch` msgspec Struct (entity-noun naming, not "DTO") in `src/py/app/domain/products/schemas/_products.py` projects `id, name, description, price, similarity_score`. `Product` already uses `price`. Unused `VectorDemoResult` removed. [6cc3ca2]
- [x] **6.3** Band-aid `r["distance"] = 1 - r["similarity_score"]` deleted from `OracleVectorSearchService.similarity_search`; controller now consumes `similarity_score` directly via attribute access on `ProductMatch`. [6cc3ca2]
- [x] **6.4** New `src/py/tests/integration/test_vector_search.py` (2 tests) seeds a known embedding, runs vector-search-products, and asserts the `ProductMatch` shape: `price > 0`, `similarity_score ∈ [0,1]`, no `current_price`/`distance` attrs, and self-query yields `similarity_score ≈ 1.0`. [6cc3ca2]
- [x] **6.5** New `src/py/tests/unit/test_vector_search_shape.py` (4 tests, no DB): static SQL projection assertions + AsyncMock service test + controller `.fn` shape test. Demo response now exposes `price` so the rename is visible to API consumers. [6cc3ca2]

### Phase 7: Patterns.md rewrite (`oracledb-vertexai-4d6.2.7`)

- [ ] **7.1** Rewrite `.agents/patterns.md` "Architecture Patterns" section. Document:
  - Three-provider Dishka layout (`LitestarPersistenceProvider`, `IntegrationsProvider`, `DomainServiceProvider`).
  - Named-SQL pattern (`db/sql/{domain}.sql` + `-- name:` + `db_manager.get_sql()`).
  - `create_filter_dependencies` for list endpoints.
  - `Inject[T]` (alias of `FromDishka[T]`) for handler injection.
  - Domain layout: `controllers/` + `services/` + `schemas/` packages.
- [ ] **7.2** Remove the false claim that "SQLSpec uses query builder" — this codebase uses **raw named SQL with .where() refinements**, not the builder.
- [ ] **7.3** Add gotcha: "Dishka REQUEST-scoped driver factories must yield via `async with config.provide_session() as driver: yield driver` — returning the driver directly leaks connections."
- [ ] **7.4** Add gotcha: "Named-SQL files are loaded once at boot. Tests that mutate `.sql` files mid-run must call `db_manager.reload_sql_files()`."

---

## Out of Scope (defer to other chapters)

- ADK runner rebuild on `Workflow`/`BaseNode` — Ch 3.
- `request_container_var` deletion — Ch 3 (it's a chat concern).
- Frontend rebuild — Ch 4.
- CLI command pruning (`bulk-embed`, `export-fixtures`) — Ch 5.
- Knowledge base archival — Ch 5.

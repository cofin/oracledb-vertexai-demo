# Flow: deadcode-sweep

*Beads: oracledb-vertexai-mzm.2*

## Specification

Delete verified zero-caller dead code with **zero behavior change**. Every symbol
below was re-verified as 0-caller by grep (see Code Analysis Summary). Each deletion
removes the symbol, its named-SQL sibling (if any), and its tests. Project rule: no
backwards-compat shims — delete completely, never re-export a stub.

Out of scope (owned by other chapters, do **not** touch here):

- `src/app/domain/products/services/maps.py` — becomes live in `maps-consolidation` (mzm.7).
- The dead `/api/chat` partials — owned by `chat-path-consolidation` (mzm.5).

### Requirements

- Remove each confirmed-dead symbol/file listed in the Code Analysis Summary.
- Remove the named-SQL sibling for each deleted query method, and drop its key from
  `test_named_sql.py`'s `EXPECTED_KEYS`.
- Delete tests that exist only to exercise a deleted symbol; **rewrite** (not delete)
  any test that mixes a deleted symbol with still-live coverage.
- Remove now-unused imports left behind by each deletion (`pydantic`, `EventListener`,
  `Scope`, `SearchMetricsCreate` local import, `datetime`/`UUID` in `_chat.py`).
- Keep `CamelizedBaseStruct` (37 uses), `ResponseCache`, `ChatMessage`,
  `CoffeeChatReply`, `store_matches_hint`, `find_stores_by_location`,
  `find_stores_with_product`, and the controller-discovery path in `domains.py`.
- `make lint && make test` green; grep confirms 0 remaining references to every
  deleted symbol.

### Code Analysis Summary

Greps run on this branch (`feat/inv`), excluding each symbol's own definition file:

| Target | Grep (whole-word, def file excluded) | Result |
| --- | --- | --- |
| `src/app/utils/sync_tools.py` | `grep -rn "sync_tools" --include="*.py" . \| grep -v "sqlspec.utils.sync_tools"` | 0 importers. The only other `sync_tools` ref is `from sqlspec.utils.sync_tools import run_` in `cli/utils.py` — a **different** module; do not touch. |
| `ApplicationError` / `lib/exceptions.py` | `grep -rn "ApplicationError" --include="*.py" src/` + `grep -rn "lib.exceptions" ...` | 0 references; 0 importers of the module. `exceptions.py` contains only `ApplicationError`. |
| `CamelizedBaseSchema`, `BaseSchema`, `camel_case`, `Message`, `BaseStruct.to_dict` | per-symbol `grep -rn "\b<sym>\b" --include="*.py" src/ \| grep -v schema.py` | 0 uses each (`Message` hits are `litestar.types.asgi_types.Message` + `"Message cannot be empty"` literals; `.to_dict()` has 0 hits). `CamelizedBaseStruct` = 37 uses → **KEEP**. |
| `domains.py` listener subsystem (`find_listeners_in_module`, `discover_domain_listeners`, `_discover_listeners_in_submodule`, `_discover_and_register_listeners`, `listener_submodules`, `discover_listeners`, `_DiscoveryState.listener_count`/`logged_listeners`, `_store_controller_results`) | per-symbol grep excluding `domains.py`; `find src/app/domain -name events.py -o -name listeners.py` | 0 external refs each. **No domain ships `events.py`/`listeners.py`**. `_store_controller_results` called exactly once (by `_discover_and_register_controllers`) → inline. `EventListener` import becomes unused. |
| `_SQLSpecPlugin` (top-level stub in `plugins.py`, lines ~41-46) | `grep -rn "_SQLSpecPlugin" --include="*.py" src/` | 0 refs. The real subclass `SQLSpecPlugin(_SQLSpecPluginBase)` is defined inside `_initialize`; the top-level stub class is never used. |
| `Scope` re-export in `lib/di.py` | `grep -rn "from app.lib.di import.*Scope\|di import Scope" --include="*.py" src/` | 0 importers; `Scope` is unused within `di.py` itself. |
| `find_stores_by_city`, `find_stores_by_state`, `search_stores_by_zip` | per-method grep excluding `services.py` | 0 callers, 0 tests each. |
| `get_store_inventory` | grep excluding `services.py` | 1 caller: `test_store_service.py:132` (test-only). |
| `StoreInventoryItem` | `grep -rn "StoreInventoryItem"` | Only `get_store_inventory` (+ its test) + `_products.py` def + `schemas/__init__.py` export → **becomes newly-dead** once `get_store_inventory` is gone. |
| named SQL `find-stores-by-city/state/zip` (`stores.sql`), `list-store-inventory` (`inventory.sql`) | `grep -rln "<key>" --include="*.sql" --include="*.py" src/` | Each referenced only by its `.sql` file, the deleted `services.py` method, and `test_named_sql.py`'s `EXPECTED_KEYS`. |
| `location_hint_matches` (`_location.py`) | `grep -rn "location_hint_matches"` | 0 refs. `store_matches_hint` (the helper it wraps) is used → KEEP. |
| `delete_expired_responses` (system `services.py`) | `grep -rn "delete_expired_responses"` + scheduler/CLI scan | **KEEP — do NOT delete** (user-confirmed). It is unwired today but will be wired to a cache-cleanup command in **Ch8**, not removed. Keep its test. |
| `_session.py` (`UserSessionCreate`, `UserSession`, `HistoryMeta`) | per-symbol grep excluding `_session.py` | Each only in `system/schemas/__init__.py` re-export → entire file dead. |
| `EmbeddingCache` (`_cache.py`) | `grep -rn "EmbeddingCache"` + traced the embedding-cache feature | **KEEP — do NOT delete.** The embedding-cache *feature* is live: `CacheService.get_embedding`/`save_embedding` (system `services.py:188-219`) are called from the embedding path (`products/services.py:279,295`) and `invalidate_cache`/`coffee clear-cache` clear `embedding_cache` alongside `response_cache`. The `EmbeddingCache` *struct* is currently un-instantiated only because `get-cached-embedding` selects just `embedding` (vs `get-cached-response` which selects the full row → `ResponseCache`). Resolution: the struct is wired into the typed read in **Ch8** (symmetric with `ResponseCache`), not deleted here. |
| `record_search_metric` (adk.py lines ~210-232) | `grep -rn "record_search_metric"` | 0 callers. Has a redundant local `from app.domain.system.schemas import SearchMetricsCreate` (line 221); the module-level import (line 60, used at 158) stays. |
| `ChatConversationCreate`, `ChatConversation` (`_chat.py`) | per-symbol grep excluding `_chat.py` | Each only in `chat/schemas/__init__.py` re-export → **0 consumers, dead**. `ChatMessage` + `CoffeeChatReply` are used → KEEP. After removal, `datetime`/`UUID` imports in `_chat.py` become unused. |

Cross-cutting notes captured during analysis:

- `test_named_sql.py` carries an `EXPECTED_KEYS` tuple AND `EXPECTED_FILES`
  (`"inventory.sql"`, `"products.sql"`, `"stores.sql"`, `"system.sql"`). Removing the
  four named queries means dropping their keys from `EXPECTED_KEYS`. `inventory.sql`
  retains `find-stores-with-product-inventory` + `find-product-availability-by-query`,
  so `EXPECTED_FILES` stays intact (do not delete any `.sql` file).
- `test_store_service.py::test_inventory_methods_return_typed_rows_and_sort_by_coordinates`
  is a **mixed** test: it exercises both `get_store_inventory` (delete) and
  `find_stores_with_product` (KEEP). Rewrite it to drop the `get_store_inventory` /
  `StoreInventoryItem` arrange-and-assert lines and the `StoreInventoryItem` import,
  while preserving the `find_stores_with_product` coordinate-ranking coverage.
- `rank-stores-by-distance` (`stores.sql`) is referenced only by `test_named_sql.py`'s
  `EXPECTED_KEYS` (no service method calls it). It is **NOT in this chapter's scope**
  (not in the Beads task); leave it untouched.
- `domains.py`: `DomainPluginConfig` keeps `discover_listeners`-driven behavior removed.
  `plugins.py::_initialize` constructs `DomainPluginConfig(domain_packages=..., discover_controllers=True, use_dishka_router=True)` and does NOT pass `discover_listeners`, so removing the field and its `on_app_init` branch requires no call-site change there.

## Implementation Plan

### Phase 1: Standalone dead files & re-exports (no SQL, no behavior)
- [ ] 1.1 Delete `src/app/utils/sync_tools.py` entirely (0 importers). Do not touch the unrelated `from sqlspec.utils.sync_tools import run_` in `src/app/cli/utils.py`.
- [ ] 1.2 Delete `src/app/lib/exceptions.py` entirely (only contained `ApplicationError`, 0 references).
- [ ] 1.3 In `src/app/lib/schema.py` delete `CamelizedBaseSchema`, `BaseSchema`, `camel_case`, `Message`, and `BaseStruct.to_dict` (leaving `BaseStruct` as an empty `msgspec.Struct` base). Remove the now-unused `from pydantic import BaseModel as _BaseModel` and `from pydantic import ConfigDict` imports, plus the unused `Any` import if it is no longer referenced. **Keep** `CamelizedBaseStruct`.
- [ ] 1.4 In `src/app/lib/di.py` remove `from dishka import Scope` and drop `"Scope"` from `__all__` (consumers import `Scope` from dishka directly).
- [ ] 1.5 In `src/app/server/plugins.py` delete ONLY the empty top-level stub class `_SQLSpecPlugin` (lines 42-47). Do NOT touch the similarly-named `_SQLSpecBase` type alias (line 25, used by the `db:` annotation at line 55) or `_SQLSpecPluginBase` (line 73, the real base for the nested `SQLSpecPlugin` at line 79). Verified: `_SQLSpecPlugin` (exact) is referenced nowhere — the 3 grep hits are 1 stub def + 2 `_SQLSpecPluginBase` substring matches.

### Phase 2: `domains.py` listener-discovery removal (keep controller discovery)
- [ ] 2.1 In `src/app/utils/domains.py` delete `find_listeners_in_module`, `discover_domain_listeners`, `_discover_listeners_in_submodule`, and `DomainPlugin._discover_and_register_listeners`.
- [ ] 2.2 Remove the `discover_listeners` and `listener_submodules` fields from `DomainPluginConfig`, and remove the `if self.config.discover_listeners: self._discover_and_register_listeners(...)` branch from `DomainPlugin.on_app_init`.
- [ ] 2.3 Remove `_DiscoveryState.listener_count` and `_DiscoveryState.logged_listeners` (attributes, their `reset()` assignments, and the `logged_listeners` log branch in `log_discovery_results`).
- [ ] 2.4 Inline `_store_controller_results` into its single caller `_discover_and_register_controllers`, then delete the method.
- [ ] 2.5 Remove the now-unused `from litestar.events import EventListener` import, and drop `discover_domain_listeners` + `find_controllers_in_module`-adjacent listener entries from `__all__` (`discover_domain_listeners`; keep controller exports).

### Phase 3: Products store dead methods + named SQL
- [ ] 3.1 In `src/app/domain/products/services/services.py` (`StoreService`) delete `find_stores_by_city`, `find_stores_by_state`, `search_stores_by_zip`, and `get_store_inventory`.
- [ ] 3.2 Delete the `find-stores-by-city`, `find-stores-by-state`, and `find-stores-by-zip` named queries from `src/app/db/sql/stores.sql`. Keep `list-stores`, `get-store-by-id`, `find-stores-by-location`, `rank-stores-by-distance`.
- [ ] 3.3 Delete the `list-store-inventory` named query from `src/app/db/sql/inventory.sql`. Keep `find-stores-with-product-inventory` and `find-product-availability-by-query`.
- [ ] 3.4 Delete the now-orphaned `StoreInventoryItem` schema from `src/app/domain/products/schemas/_products.py` and remove its import + `__all__` entry from `src/app/domain/products/schemas/__init__.py`. Remove the unused `StoreInventoryItem` import from `services.py` if present.
- [ ] 3.5 In `src/app/domain/products/services/_location.py` delete `location_hint_matches` (0 refs). Keep `haversine_miles` and `store_matches_hint`.

### Phase 4: System service + dead schema structs
- [ ] 4.1 **KEEP `CacheService.delete_expired_responses`** — not deleted in this chapter (user-confirmed). It is wired into a cache-cleanup command in Ch8. No change here.
- [ ] 4.2 Delete `src/app/domain/system/schemas/_session.py` entirely, and remove `from ._session import HistoryMeta, UserSession, UserSessionCreate` plus the `"HistoryMeta"`, `"UserSession"`, `"UserSessionCreate"` `__all__` entries from `src/app/domain/system/schemas/__init__.py`.
- [ ] 4.3 **KEEP `EmbeddingCache`** in `src/app/domain/system/schemas/_cache.py` and its `__init__` export. The embedding-cache feature is live (see Code Analysis); the struct is wired into the typed read in **Ch8** rather than deleted here. No change in this chapter.

### Phase 5: Chat dead struct + adk method
- [ ] 5.1 In `src/app/domain/chat/schemas/_chat.py` delete `ChatConversationCreate` and `ChatConversation` (0 consumers). Remove the now-unused `from datetime import datetime` and `from uuid import UUID` imports. Keep `ChatMessage` and `CoffeeChatReply`.
- [ ] 5.2 In `src/app/domain/chat/schemas/__init__.py` remove `ChatConversation`/`ChatConversationCreate` from the `from ._chat import (...)` block and from `__all__`.
- [ ] 5.3 In `src/app/domain/chat/services/adk.py` delete the `record_search_metric` method (lines ~210-232), including its redundant local `from app.domain.system.schemas import SearchMetricsCreate`. Leave the module-level `SearchMetricsCreate` import (line 60) — it is used by the live `search_products_by_vector` path (~line 158).

### Phase 6: Test removal / rewrite + named-SQL test sync
- [ ] 6.1 Remove the `find-stores-by-city`, `find-stores-by-state`, `find-stores-by-zip`, and `list-store-inventory` entries from `EXPECTED_KEYS` in `src/tests/unit/app/db/test_named_sql.py`. Do not modify `EXPECTED_FILES`.
- [ ] 6.2 Rewrite `src/tests/unit/app/domain/products/services/test_store_service.py::test_inventory_methods_return_typed_rows_and_sort_by_coordinates`: drop the `get_store_inventory` call, the `StoreInventoryItem` fixture/asserts, and the `StoreInventoryItem` import; keep and preserve the `find_stores_with_product` coordinate-ranking assertions (rename the test if it no longer covers "inventory methods" plural).
- [ ] 6.3 **KEEP** the `delete_expired_responses` test in `test_cache.py` (the method is retained and wired in Ch8). No test change here.
- [ ] 6.4 Search test trees for any reference to the deleted schema structs (`UserSession*`, `HistoryMeta`, `ChatConversation*`) and the schema.py symbols (`CamelizedBaseSchema`, `BaseSchema`, `camel_case`); remove any orphaned references. (Analysis found none, but re-confirm post-deletion.) Do NOT touch `EmbeddingCache` references — it is kept.

### Phase 7: Gate
- [ ] 7.1 Run `make lint` and fix any unused-import / `__all__` fallout introduced by the deletions.
- [ ] 7.2 Run `make test` and confirm green.

## Acceptance

- [ ] All listed symbols/files deleted; mixed test rewritten; test-only tests removed.
- [ ] `make lint && make test` green.
- [ ] Each grep below returns **no results** (or only the expected non-target lines noted):
  - `grep -rn "sync_tools" --include="*.py" src/ | grep -v "sqlspec.utils.sync_tools"` → empty
  - `grep -rn "ApplicationError" --include="*.py" src/` → empty
  - `grep -rn "CamelizedBaseSchema\|\bBaseSchema\b\|\bcamel_case\b" --include="*.py" src/` → empty
  - `grep -rn "\.to_dict()" --include="*.py" src/` → empty
  - `grep -rn "from app.lib.di import.*Scope\|di import Scope" --include="*.py" src/` → empty
  - `grep -rn "_SQLSpecPlugin" --include="*.py" src/` → empty
  - `grep -rn "find_listeners_in_module\|discover_domain_listeners\|_discover_listeners_in_submodule\|_discover_and_register_listeners\|listener_submodules\|\bdiscover_listeners\b\|listener_count\|logged_listeners\|_store_controller_results" --include="*.py" src/` → empty
  - `grep -rn "find_stores_by_city\|find_stores_by_state\|search_stores_by_zip\|get_store_inventory\|StoreInventoryItem" --include="*.py" src/` → empty
  - `grep -rn "find-stores-by-city\|find-stores-by-state\|find-stores-by-zip\|list-store-inventory" --include="*.sql" --include="*.py" src/` → empty
  - `grep -rn "location_hint_matches" --include="*.py" src/` → empty
  - `grep -rn "delete_expired_responses" --include="*.py" src/` → empty
  - `grep -rn "UserSessionCreate\|\bUserSession\b\|HistoryMeta" --include="*.py" src/` → empty
  - `grep -rn "ChatConversationCreate\|\bChatConversation\b" --include="*.py" src/` → empty
  - `grep -rn "record_search_metric" --include="*.py" src/` → empty
- [ ] `grep -rn "CamelizedBaseStruct" --include="*.py" src/` still returns its 37 live uses (no regression).
- [ ] `src/app/domain/products/services/maps.py` and the `/api/chat` partials are untouched.

## Verification

```bash
make lint
make test
# Spot-check zero-residue (each should print nothing):
grep -rn "sync_tools" --include="*.py" src/ | grep -v "sqlspec.utils.sync_tools"
grep -rn "ApplicationError\|location_hint_matches\|delete_expired_responses\|record_search_metric" --include="*.py" src/
grep -rn "find_stores_by_city\|find_stores_by_state\|search_stores_by_zip\|get_store_inventory\|StoreInventoryItem" --include="*.py" src/
grep -rn "UserSessionCreate\|\bUserSession\b\|HistoryMeta\|ChatConversationCreate\|\bChatConversation\b" --include="*.py" src/
grep -rn "find-stores-by-city\|find-stores-by-state\|find-stores-by-zip\|list-store-inventory" --include="*.sql" --include="*.py" src/
# Confirm kept symbol survives:
grep -rc "CamelizedBaseStruct" --include="*.py" src/ | grep -v ':0$'
```

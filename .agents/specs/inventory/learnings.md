# Learnings: Inventory Enablement

## 2026-06-13 20:40 - Flow Refresh Beads Alignment

- **Changed:** Recreated missing local Beads records for the inventory saga and synchronized `.agents/flows.md`, `progress.md`, and child metadata files.
- **Why:** The tracked specs showed inventory data and grounding as complete, with inventory RAG/UI still planned, but the local Beads DB had no active inventory records.
- **Files changed:** `.agents/flows.md`, `.agents/specs/inventory*/metadata.json`, `.agents/specs/inventory/progress.md`.
- **Commands:** `bd status`, `bd list --all --json`, focused unit refresh tests.
- **Gotchas:** Explicit Beads IDs must use the repository prefix (`oracledb-vertexai-`). Create explicit IDs first, then attach parents with `bd update <id> --parent <parent>`.

## 2026-06-23 - Inventory RAG And HTMX Dashboard

- **Implemented:** Store-aware vector search, inventory-enriched ProductMatch rows, RAG grounding that resolves the active store from safe location context, stock-status wording in grounded product answers, a store inventory service/query, and an HTMX inventory panel on `/explore`.
- **Files changed:** `src/app/db/sql/{products,inventory}.sql`, `src/app/domain/{chat,products,web}/...`, `src/app/domain/web/templates/pages/explore.html.j2`, `src/app/domain/web/templates/partials/_inventory_list.html.j2`, focused unit and integration tests.
- **Commands:** `uv run pytest src/tests/unit/app/domain/web/controllers/test_pages.py src/tests/unit/app/domain/products/controllers/test_store_inventory.py src/tests/unit/app/domain/products/controllers/test_vector.py src/tests/unit/app/domain/products/services/test_store_service.py src/tests/unit/app/domain/chat/services/test_adk.py src/tests/unit/app/domain/chat/services/test_adk_grounding.py -q`; `uv run mypy src/app tools manage.py`; `uv run pyright src/app tools manage.py`; `uv run ruff check src/app tools src/tests/unit src/tests/integration/app/domain/web/controllers/test_pages.py`.
- **Gotchas:** Store-aware product RAG must bypass the response cache whenever safe location or store context is present; otherwise a cached Dallas answer can be reused for another store. Inventory UI store selectors must come from `StoreService.get_all_stores()` and fixtures, never from hardcoded template presets. The page may render an empty selector if store data is unavailable, but it must not freeze a hand-picked list of locations into the template.
- **Verification limits:** The targeted unit/type/lint checks passed. The integration page test still needs the normal Vite manifest/assets environment and a fresh Oracle pool/event-loop setup; otherwise it fails before exercising the new inventory behavior.

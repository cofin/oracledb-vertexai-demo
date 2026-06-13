# Research: Inventory Implementation Options for Cymbal Coffee

## Executive Summary
*   **Current State:** Inventory infrastructure (tables, SQL, services) is 80% implemented but underutilized in the user-facing chat and explore flows.
*   **Key Finding:** `PRODUCT_RAG` recommendations are not inventory-aware, potentially leading the AI to recommend out-of-stock items.
*   **Opportunity:** Grounding chat in store-specific inventory and providing a "Live Inventory" dashboard would significantly enhance the demo's realism.
*   **Risk:** High-frequency inventory updates in a demo environment need to be handled gracefully (e.g., via simple simulate-and-reset patterns).

## Codebase Analysis

### Relevant Modules
- `src/app/db/sql/inventory.sql`: Core SQL queries for inventory lookups.
- `src/app/domain/products/services/services.py`: `StoreService` handles inventory business logic.
- `src/app/domain/chat/services/adk.py`: `AgentToolsService` and `ADKRunner` orchestrate inventory-aware chat.
- `src/app/db/migrations/0001_...sql`: Defines the `store_product_inventory` table.

### Existing Patterns
- **Named SQL:** All database interaction uses `db_manager.get_sql("name")`.
- **HTMX Partials:** Web views are composed of small J2 partials triggered by HTMX events.
- **ADK Intent Classification:** Chat uses a Flash-Lite classifier to route to deterministic or LLM-driven events.

### Reusable Components
- `ProductAvailability` schema: Comprehensive model for store + product + distance data.
- `_rank_availability` helper: Ranks results by distance if coordinates are available.

### Internal Dependencies
- `StoreService` depends on `ProductService` via common `db_manager` patterns.
- `ADKRunner` depends on `AgentToolsService` for closure-bound tool execution.

### Constraints
- **Oracle 26ai:** Must use standard SQL bind parameters (:name).
- **Coordinate Privacy:** Browser coordinates are request-scoped and must not be persisted.

## Library Documentation

### Litestar / HTMX
- **SSE:** Already used for chat streaming; can be reused for real-time inventory "ticker" if desired.
- **HTMX `hx-trigger`:** Useful for refreshing inventory views on product/store selection.

### Oracle 26ai
- **VECTOR(3072, FLOAT32):** Used for products; could be used to find "similar available products" if the requested one is out of stock.

## Prior Art

### Internal References
- `PRODUCT_AVAILABILITY` intent in `adk.py`: A good starting point for deterministic inventory answers.
- `0001` migration: Contains the initial bootstrap of inventory data.

### Recommended Approach
Based on research, the recommended approach is to **implement Inventory-Aware RAG** and a **Store Inventory Dashboard**.

**Rationale:** This provides both "magic" (AI recommending what's actually there) and "utility" (a clear view of store status), fulfilling the demo's goals as a reference application.

## Risk Assessment

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Vector search performance with Joins | Low | Med | Use proper indexing (already exists in 0001) and Oracle 26ai INMEMORY features. |
| Inconsistent Data | Med | Med | Ensure fixtures are robust and CLI 'upgrade' resets sequences correctly. |
| Over-complex Chat Routing | Med | High | Keep `PRODUCT_RAG` and `PRODUCT_AVAILABILITY` distinct but share grounding logic. |

### Integration Risks
- **HTMX State:** Ensuring the "Explore" page stays responsive when adding more panels.

### Recovery Strategy
**Rollback Plan:** Revert changes to `services.py` and `adk.py`.
**Checkpoint Strategy:** Verify `PRODUCT_RAG` remains functional before adding inventory filtering.
**Dependencies to Consider:** `adk_sessions` and `app_session` tables.

## Open Questions
- Should we allow "fake buying" in the demo to deplete inventory?
- Do we need a "Global Inventory" view or just store-by-store?

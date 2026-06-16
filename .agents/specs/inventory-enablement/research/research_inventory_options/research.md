## Codebase Analysis

### Relevant Modules
- `app.domain.products.services.StoreService`: Main entry point for inventory and availability logic.
- `app.domain.chat.services.ADKRunner`: Handles `PRODUCT_AVAILABILITY` intent classification and deterministic grounding.
- `app.domain.products.schemas`: Defines `StoreInventoryItem` and `ProductAvailability` data contracts.
- `app.db.migrations.0001`: Contains the `store_product_inventory` table definition.

### Existing Patterns
- **Named SQL**: Inventory queries are stored in `src/app/db/sql/inventory.sql`.
- **Deterministic Routing**: Intent classification routes stock queries to precise SQL lookups before reaching the LLM.
- **Camelized Schemas**: All data contracts use `CamelizedBaseStruct` for frontend compatibility.

### Reusable Components
- `haversine_miles`: Utility in `src/app/domain/products/services/_location.py` for proximity ranking.
- `renderStoreCard`: Frontend JS component for displaying store availability in chat.

### Internal Dependencies
- `StoreService` depends on `ProductService` for ID/name lookups during availability checks.
- `ADKRunner` depends on `StoreService` via `AgentToolsService` for grounding.

### Constraints
- **Data Sparsity**: Fixtures only cover stores 1, 4, 13, and 16.
- **Model Isolation**: Inventory data is purely relational; it is not yet indexed in vector search (nor should it be, as it is highly volatile).

## Library Documentation

### Oracle 26ai
**Relevant APIs:**
- `VECTOR(3072, FLOAT32)`: Used for products, but could be used to rank stores by "flavor profile" in the future.
- `BOOLEAN`: Native boolean type used for `pickup_available` and `in_stock`.
- `INMEMORY`: Tables are flagged for `INMEMORY PRIORITY HIGH` to ensure millisecond latency for grounding lookups.

### Litestar
**Relevant APIs:**
- `HTMXTemplate`: Used to render partials for inventory cards.
- `ServerSentEvent`: Used to stream the final grounded answer.

## Prior Art

### Internal References
- `PRODUCT_RAG` implementation in `_adk_grounding.py` provides a template for grounded turn generation.

### Recommended Approach
Focus on **Data Population** and **Dashboard Visibility**. The infrastructure is robust, but the demo feels "empty" because most searches return "no availability" due to sparse fixtures.

**Rationale:** The technical risk is low because the code is already written and tested. The primary value-add is making the demo "alive" with consistent data across all stores.

## Risk Assessment

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data inconsistency between catalog and inventory | Med | Low | Automated fixture generator script |
| Performance degradation with 10k+ inventory rows | Low | Low | SQL indexing and INMEMORY are already in place |
| Coordinate privacy | Low | High | Use request-scoped coordinates only; never persist |

### Integration Risks
- Breaking changes to `ProductAvailability` schema would require updates to both Python and JS.

### Recovery Strategy
**Rollback Plan:** Standard git revert and migration downgrade.
**Checkpoint Strategy:** Verify chat availability after loading new fixtures.
**Dependencies to Consider:** `ADKRunner` must be tested against new inventory data to ensure formatting handles large result sets.

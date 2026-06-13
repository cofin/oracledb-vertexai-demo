# Flow: inventory-rag

## Specification
The current `PRODUCT_RAG` flow recommends products based purely on vector similarity, ignoring inventory. This flow will integrate inventory awareness into the RAG pipeline to ensure recommendations are grounded in product availability at the user's store.

### Requirements
*   Create an inventory-aware vector search query.
*   Allow filtering by `store_id` to check availability at a specific store.
*   Annotate product recommendations with their stock status.
*   Fall back to general availability if no specific store is targetted.

### Code Analysis Summary
*   Current vector search: `vector-search-products` in `products.sql`.
*   Current grounding: `_ground_product_rag_turn` in `_adk_grounding.py`.
*   Service: `AgentToolsService.search_products_by_vector` in `adk.py`.
*   Schema: `ProductMatch` in `src/app/domain/products/schemas/_products.py`.

## Implementation Plan

### Phase 1: Schema & SQL Updates
- [ ] 1.1 Modify `ProductMatch` schema to include optional inventory fields: `quantity_available: int | None = None`, `stock_status: StockStatus | None = None`, `pickup_available: bool | None = None`.
- [ ] 1.2 Add `vector-search-products-by-store` query to `src/app/db/sql/products.sql` that `JOIN`s with `store_product_inventory` and filters by `store_id`.

### Phase 2: Service & Tool Updates
- [ ] 2.1 Update `ProductService.search_by_vector` to accept `store_id: int | None = None`. If `store_id` is provided, use `vector-search-products-by-store` query; otherwise use `vector-search-products`.
- [ ] 2.2 Update `AgentToolsService.search_products_by_vector` signature to accept `store_id: int | None = None` and pass it to `ProductService`.
- [ ] 2.3 Update tool factories in `ADKRunner._make_tool_factories` to resolve `store_id` using `StoreService.resolve_store(location_context)` and pass it to the search tool.

### Phase 3: ADK Grounding Updates
- [ ] 3.1 Update `_ground_product_rag_turn` in `src/app/domain/chat/services/_adk_grounding.py` to receive `location_context`.
- [ ] 3.2 Resolve store in `_ground_product_rag_turn` and pass `store_id` to fallback search if it runs.
- [ ] 3.3 Update `_grounded_product_answer` to check `stock_status` in product results and append stock status to the recommendation if present (e.g. "In Stock at Dallas Arts District" or "Out of Stock at this location").

### Phase 4: Verification
- [ ] 4.1 Create integration test `src/tests/integration/test_inventory_rag.py` to verify RAG responses are inventory-aware.
- [ ] 4.2 Run tests with `uv run pytest src/tests/integration/test_inventory_rag.py`.

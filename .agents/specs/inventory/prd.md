# Master PRD: Inventory Enablement

## 1.0 Context
The Cymbal Coffee demo aims to showcase Oracle 26ai vector search and Vertex AI capabilities. While the database infrastructure and services for inventory are roughly 80% implemented, they are underutilized. The demo currently lacks realistic inventory data (fixtures only cover a few stores) and the chat assistant (`PRODUCT_RAG`) is not aware of product availability, leading to recommendations for out-of-stock items.

## 2.0 North Star Goal
Enable comprehensive, real-time inventory awareness across the Cymbal Coffee demo, making the chat assistant recommend available products and providing users with clear visibility into store-specific stock.

## 3.0 Roadmap (Saga Chapters)

### Chapter 1: Data Foundation & Fixtures (`inventory-data`)
*   **Goal**: Populate the database with realistic inventory data for all stores.
*   **Deliverables**: Updated fixtures and a script to generate consistent inventory data mapped to catalog products and store locations.
*   **Success Criteria**: All stores have inventory records for a representative subset of products.

### Chapter 2: Deterministic Availability Routing (`inventory-grounding`)
*   **Goal**: Ground chat responses in actual inventory data for availability queries.
*   **Deliverables**: Implementation of `PRODUCT_AVAILABILITY` intent handling in `ADKRunner` using named SQL lookups.
*   **Success Criteria**: Queries like "Is cold brew in stock at store X?" return accurate answers based on the database.

### Chapter 3: Inventory-Aware RAG (`inventory-rag`)
*   **Goal**: Ensure product recommendations only include in-stock items or clearly indicate availability.
*   **Deliverables**: Update vector search queries and the RAG pipeline to join with inventory data and filter/annotate results.
*   **Success Criteria**: The assistant recommends products available at the user's specified or nearest store.

### Chapter 4: Live Inventory Dashboard (`inventory-ui`)
*   **Goal**: Provide visual visibility into store stock.
*   **Deliverables**: HTMX partials and UI components to display inventory status per product and store.
*   **Success Criteria**: Users can see a "Live Inventory" view in the store details or search results.

## 4.0 Global Constraints
*   **Database**: Must use named SQL stored in `src/app/db/sql/` and mapped via SQLSpec.
*   **Oracle 26ai**: Leverage native boolean types and `INMEMORY` features where appropriate for latency.
*   **Privacy**: Browser coordinates must remain request-scoped and never be persisted in history, cache, or logs.
*   **Performance**: Ensure vector search with joins remains highly performant.

## 5.0 Assumptions
*   The user is AFK and prefers a complete PRD based on existing research.
*   We are proceeding in markdown-only mode as the Beads CLI check failed.

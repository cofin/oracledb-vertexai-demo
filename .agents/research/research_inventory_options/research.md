# Research: Options for Enabling Inventory

## Executive Summary
- **Current State**: The infrastructure for inventory management is present in the schema (`store_product_inventory`), services (`StoreService`), and ADK grounding, but the data is sparse and the feature is not fully utilized in the UI or Chat.
- **Data Gap**: Existing fixtures for inventory are minimal. Enabling inventory requires a strategy for populating realistic demo data.
- **Architectural Opportunities**: Oracle 26ai features like JSON Relational Duality Views and In-Memory optimization can be leveraged to modernize the inventory stack.
- **UX Opportunities**: The chat UI and Web UI need dedicated components to display product availability and store-level stock.

## Codebase Analysis

### Relevant Modules
- `src/app/db/migrations/0001_cymball_coffee_products.sql`: Defines the `store_product_inventory` table.
- `src/app/domain/products/services/services.py`: `StoreService` provides methods for querying inventory (`get_store_inventory`, `find_product_availability`).
- `src/app/domain/chat/services/adk.py`: Handles `PRODUCT_AVAILABILITY` intent using `StoreService`.
- `src/app/domain/chat/services/_adk_grounding.py`: Formats the inventory answer for the LLM.

### Existing Patterns
- **SQLSpec Services**: Repository-style services using named SQL files.
- **ADK Intent Routing**: Deterministic intent detection for availability queries.
- **Dishka DI**: Dependency injection for services and ADK runner.

### Reusable Components
- `StoreService`: Can be extended with more complex inventory logic.
- `ProductAvailability` schema: Good foundation for UI data binding.

### Constraints
- Sparse data in `store_product_inventory.json.gz`.
- No current UI representation of inventory results in HTMX partials.

## Options for Enabling Inventory

### 1. Data Enrichment (Synthetic Generation)
- **Description**: Create a script to generate a full mesh of inventory data (every product in every store) with randomized stock levels.
- **Rationale**: Ensures the demo always has "hits" when searching for product availability.

### 2. Oracle 23ai/26ai JSON Relational Duality Views
- **Description**: Create a Duality View that exposes store inventory as a single JSON document.
- **Rationale**: Showcases Oracle's ability to serve JSON-native apps while maintaining relational integrity.

### 3. Dynamic Inventory Mock (Drift Simulation)
- **Description**: A scheduled task that "sells" products or "restocks" them periodically.
- **Rationale**: Makes the demo feel "alive" and interactive.

### 4. Enhanced Chat Grounding & UI
- **Description**: Update the ADK grounding to handle edge cases (e.g., product out of stock at nearest store but available nearby) and update the UI to render inventory cards.
- **Rationale**: Improves the user experience and demonstrates the "Store-Aware" capability of the agent.

## Risk Assessment

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data Mismatch | Medium | Medium | Use a single source of truth for synthetic generation. |
| Performance Hit | Low | Medium | Leverage Oracle In-Memory for inventory queries. |
| UI Clutter | Medium | Low | Use collapsible cards or chips for inventory results. |

### Integration Risks
- **HTMX Sync**: Ensuring the chat results and product list stay in sync if inventory changes.

### Recovery Strategy
- **Rollback Plan**: Migration `0001` is already in place; any new Duality Views or SQL changes can be added in a new migration.
- **Checkpoint Strategy**: Commit the synthetic data generator before applying it to the baseline fixtures.

## Recommended Approach
1. **Short-term**: Implement a synthetic data generator to populate `store_product_inventory` with realistic data for the Dallas market (as mentioned in `AGENTS.md`).
2. **Mid-term**: Update the Chat UI to render `inventory_results` using dedicated HTMX partials.
3. **Showcase**: Implement a JSON Relational Duality View for "Store Inventory at a Glance" to demonstrate Oracle 26ai capabilities.

## Open Questions
- Should we support "Reservations" or "Orders" as part of the inventory flow?
- Do we need to handle "Pickup" vs "Delivery" availability explicitly in the demo?

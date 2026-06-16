# Flow Spec: inventory-grounding (Stock Lookup)

## 1.0 Context
This flow implements deterministic stock lookup as outlined in Chapter 2 of the [Inventory Enablement PRD](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/.agents/specs/inventory/prd.md). It ensures that queries about product availability at specific stores are answered accurately using database queries rather than relying on LLM generation alone.

## 2.0 Requirements
- Classify user queries for product availability (e.g., "Is cold brew in stock at the Dallas store?").
- Route these queries to a deterministic handler.
- Query the database to check availability of the specified product at the specified store (or nearest stores if none specified).
- Format a user-friendly answer summarizing availability.

## 3.0 Prerequisites
- **Data Foundation**: The `inventory-data` flow must be completed, or at least have some inventory data loaded for testing.

## 4.0 Proposed Changes

### Component: Chat Domain

### Component: Chat Domain

#### [MODIFY] [adk.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/src/app/domain/chat/services/adk.py)
- Update `_product_availability_event` to query availability.
- If a target store is resolved (via location hint or coordinates) but is out of stock, retrieve alternative stores that have the product in stock.
- Update `_format_availability_answer` signature to accept target store availability and alternative in-stock stores.

#### [MODIFY] [_adk_grounding.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/src/app/domain/chat/services/_adk_grounding.py)
- Refine `_format_availability_answer` to:
    - Avoid saying "Product is available at Store (Out Of Stock)".
    - Say "Product is out of stock at Store" if quantity is 0 or status is OUT_OF_STOCK.
    - If out of stock, and alternatives are provided, append "However, it is in stock at [Alternative Store] (X miles away)."

### Component: Products Domain

#### [MODIFY] [services.py](file:///usr/local/google/home/codyfincher/code/google/oracledb-vertexai-demo/src/app/domain/products/services/services.py)
- Add `resolve_store` helper to `StoreService` (as planned in RAG).
- Ensure `StoreService.find_product_availability` can return both filtered and unfiltered results if needed.

## 5.0 Implementation Plan

### Phase 0: Base Grounding Setup
- [x] **Task 5**: Define store coordinates/hours tools and grounding node logic



### Phase 1: Store Service Refinement
- [x] **Task 1.1**: Add `resolve_store(location_context)` to `StoreService` to resolve a single store from context (by name or nearest).
- [x] **Task 1.2**: Update `find_product_availability` to return all stores, and let the caller filter.


### Phase 2: Grounding and Formatting Updates
- [x] **Task 2.1**: Update `_product_availability_event` in `adk.py` to get all stores, filter to target, and find alternative `IN_STOCK` store if target is out of stock.
- [x] **Task 2.2**: Update `_format_availability_answer` in `_adk_grounding.py` to format the message clearly (handling out of stock and alternatives).
- [x] **Task 2.3**: Update unit tests in `src/tests/unit/test_adk_grounding.py` to verify these formatting cases.

## 6.0 Verification Plan

### Automated Tests
- Run `uv run pytest src/tests/unit/test_adk_grounding.py`.

### Manual Verification
- Query: "Is cold brew in stock at Dallas Arts District?" (when it is out of stock there but in stock elsewhere).
- Verify the response suggests the alternative store.

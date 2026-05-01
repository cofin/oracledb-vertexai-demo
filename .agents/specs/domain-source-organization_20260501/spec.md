# Flow: Domain Source Organization

*Flow ID: `domain-source-organization_20260501`*
*Chapter 3 of [demo-source-organization_20260501](../demo-source-organization_20260501/prd.md)*
*Beads: `oracledb-vertexai-8jt.3`*
*Depends on: `source-organization-contract_20260501`*
*Status: Planned*

---

## Objective

Make domain modules show the demo's public behavior first: route controllers,
service capabilities, schemas, and response contracts before private request
parsing or formatting mechanics.

---

## Primary Files

- `src/app/domain/chat/controllers/_chat.py`
- `src/app/domain/products/controllers/_products.py`
- `src/app/domain/products/controllers/_vector.py`
- `src/app/domain/products/services/services.py`
- `src/app/domain/products/services/maps.py`
- `src/app/domain/products/schemas/_products.py`
- `src/app/domain/system/controllers/_metrics.py`
- `src/app/domain/web/controllers/_pages.py`
- Matching tests under `src/tests/unit/app/domain/...` and
  `src/tests/integration/app/domain/...`.

---

## Requirements

- Controller files should lead with controller classes. Helpers such as
  `_payload_value`, `_chat_form_from_request`, `_metrics_badges`,
  `_is_expected_service_unavailable`, `_unavailable_plan`, and
  `_vector_query_from_request` should move to focused private controller helper
  modules or below the controller class when that keeps the file simple.
- `src/app/domain/products/services/services.py` should make `ProductService`,
  `StoreService`, `VertexAIService`, and `OracleVectorSearchService` the visible
  story. Haversine distance and location-hint matching can move to a private
  location helper module.
- Maps URL helpers should be organized so `build_store_search_url()` and
  `build_store_directions_url()` are the visible public API.
- `MetricsController.get_metrics_summary()` should not hide trend logic as a
  nested function if a small private helper is clearer.
- Schema files may stay class-first. If grouping is adjusted, keep related
  product, store, inventory, vector, and explain-plan schemas in a reader-friendly
  order.
- Preserve named SQL usage, typed schema mapping, handler-argument injection, and
  HTMX response contracts.

---

## Implementation Plan

1. Write/update focused tests:
   - Extend controller tests that currently cover chat/vector partials.
   - Extend product service unit tests around store ranking and Maps URL helpers.
   - Update `test_source_organization.py` allowlist for fixed domain files.
2. Extract controller helpers:
   - For chat controller helpers, prefer
     `src/app/domain/chat/controllers/_helpers.py` or more specific private
     modules if responsibilities split cleanly.
   - For vector controller helpers, prefer
     `src/app/domain/products/controllers/_vector_helpers.py`.
   - Keep controller imports package-private and avoid exporting helpers from
     `controllers/__init__.py`.
3. Extract product service helpers:
   - Move distance and location matching into a private product/location helper.
   - Keep service methods using named SQL and typed `schema_type=`.
   - Keep Maps URL builders public in `services/maps.py`, with private URL
     formatting helpers below or in a sibling private module.
4. Revisit small nested helpers:
   - Move metrics trend calculation to a private helper if it improves scan order.
   - Move vector plan row `cell()` helper out of `parse_plan_rows()` if the method
     reads better with a module helper.
5. Run focused verification:
   - `uv run pytest src/tests/unit/app/domain/products src/tests/unit/app/domain/chat src/tests/unit/app/domain/system -q`
   - `uv run pytest src/tests/integration/app/domain/chat/controllers src/tests/integration/app/domain/products/controllers src/tests/integration/app/domain/web/controllers -q`
   - `uv run pytest src/tests/unit/app/test_source_organization.py -q`
   - `uv run ruff check src/app/domain`

---

## Acceptance Criteria

- Domain controller files show public controllers before private mechanics.
- Product/store service files show public service classes before helper logic.
- No endpoint route, response payload, SQL key, or schema field changes.
- Domain source organization allowlist entries are removed or justified.
- Focused domain tests and Ruff pass.

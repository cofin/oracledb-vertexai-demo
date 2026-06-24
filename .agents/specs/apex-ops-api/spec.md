# Flow Spec: apex-ops-api

*Beads: `oracledb-vertexai-apxo.3`*
*Parent PRD: [../apex-ops-console/prd.md](../apex-ops-console/prd.md)*
*Depends on: `apex-runtime-hardening`*
*Status: Planned - implementation-ready*

---

## Context

The current Litestar app already exposes product, store, vector, and chat
behavior, but those routes are shaped for HTMX and browser chat. APEX needs a
stable JSON surface that works well as a REST Source Catalog.

Current anchors:

- `src/app/domain/products/controllers/_products.py` exposes list products and
  list stores.
- `src/app/domain/products/controllers/_vector.py` exposes vector demo search
  and explain-plan behavior, but it is not the desired APEX contract.
- `src/app/domain/chat/controllers/_chat.py` exposes SSE chat and must not be
  the APEX integration surface.
- `src/app/domain/products/services/services.py` already contains product,
  store, inventory, availability, embedding, vector search, and explain-plan
  service logic.
- `src/app/domain/products/schemas/_products.py` contains schemas that can be
  reused or extended.

Official Oracle guidance to use:

- Oracle Skills `db/features/vector-search.md` and `db/features/dbms-vector.md`
  for Oracle vector-search terminology.
- Oracle Skills `db/ords/ords-rest-api-design.md` and
  `db/ords/ords-metadata-catalog.md` when shaping REST behavior that APEX and
  ORDS users will recognize.

## Requirements

- Add APEX-specific JSON endpoints without breaking existing HTMX or chat
  endpoints.
- Keep response schemas stable, typed, and OpenAPI-friendly.
- Avoid SSE and browser-session coupling.
- Expose the same coffee data:
  - products
  - stores
  - store inventory
  - product availability
  - vector recommendations
  - explain/status data
  - model/provider status
- Use deterministic fallbacks when Vertex AI credentials or model calls are not
  available.

## Proposed Endpoint Surface

Base path: `/api/apex`

- `GET /products`
  - product catalog rows
  - filters: `q`, `category`, `limit`, `offset`
- `GET /stores`
  - seeded store data with coordinates/place IDs already safe for demo use
- `GET /inventory/summary`
  - inventory counts by store and stock status
- `GET /stores/{store_id:int}/inventory`
  - inventory rows for a store
- `GET /products/{product_id:int}/availability`
  - availability across stores for one product
- `POST /recommendations`
  - request: query text, optional store id, optional limit
  - response: vector recommendations with grounded product/store data
- `GET /vector/status`
  - embedding model, dimension, provider configuration status, and Oracle vector
    search readiness
- `GET /openapi/status`
  - catalog metadata and current API version for APEX display

## Proposed Changes

- Add a controller such as
  `src/app/domain/products/controllers/_apex.py`.
- Add schemas such as
  `src/app/domain/products/schemas/_apex.py` if existing product schemas become
  overloaded.
- Add service methods only where existing product/store/vector services do not
  already provide the needed data shape.
- Register explicit operation IDs and tags so APEX REST Source Catalog entries
  are readable.
- Keep endpoint names plain and stable; avoid chat-internal route naming.

## Implementation Tasks

- [ ] Define APEX-specific request/response schemas.
- [ ] Add `/api/apex/*` controller and route registration.
- [ ] Implement inventory summary and availability endpoints through existing
  service boundaries.
- [ ] Implement recommendations endpoint through existing embedding/vector
  services with deterministic fallback behavior.
- [ ] Add operation IDs and OpenAPI schema metadata.
- [ ] Add unit/API tests for happy path and unavailable AI credentials.

## Verification

Automated:

```bash
uv run pytest src/tests/api/test_apex_ops_api.py
uv run pytest src/tests/unit/domain/products
make lint
```

Manual:

```bash
uv run coffee run
curl -fsS http://localhost:8000/api/apex/products
curl -fsS http://localhost:8000/api/apex/stores
curl -fsS http://localhost:8000/api/apex/vector/status
```

## Done

- APEX has a stable JSON API surface that does not depend on SSE chat or HTMX
  responses.
- OpenAPI output has useful operation IDs and schema names.
- Existing browser/demo routes continue to behave as before.

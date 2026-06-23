# Flow Spec: apex-ops-app

*Beads: `oracledb-vertexai-apxo.5`*
*Parent PRD: [../apex-ops-console/prd.md](../apex-ops-console/prd.md)*
*Depends on: `apexlang-lifecycle`, `apex-ops-api`, `apex-schema-bridge`*
*Status: Planned - implementation-ready after dependencies*

---

## Context

The APEX app should be a practical operations console for the same Cymbal
Coffee data shown by Litestar. It is not a replacement storefront and should
not reimplement business logic already owned by the app services.

Source root:

- `src/apex/cymbal-coffee-ops/`

Official guidance to use:

- Oracle Skills `apex` domain and APEXlang generation workflow.
- SQLcl APEXlang validation before import.
- APEX REST Source Catalog docs for consuming the filtered OpenAPI contract.

## Product Shape

App name: `Cymbal Coffee Operations Console`

Audience:

- Demo operators
- Workshop attendees learning Oracle APEX + ORDS + OpenAPI
- Engineers comparing APEX to the Litestar HTMX/ADK experience

Primary pages:

- Home / runtime status
- Products
- Stores
- Store inventory
- Low-stock and out-of-stock views
- Product availability
- Vector recommendations
- API catalog health
- Model/provider status

## Requirements

- APEX app source is tracked as APEXlang under `src/apex/cymbal-coffee-ops/`.
- APEX consumes the filtered OpenAPI catalog from the Litestar app.
- Pages show real product/store/inventory/vector/model data.
- APEX pages should make the bridge visible: users can see API/catalog health
  and where the data comes from.
- Do not make APEX depend on SSE chat.
- Do not store browser coordinates or user location in APEX.
- Keep custom PL/SQL minimal and only for APEX wiring where necessary.

## Proposed App Pages

- Dashboard
  - ORDS/APEX/runtime status
  - current API catalog version
  - model/provider status
- Product Catalog
  - interactive report over `/api/apex/products`
  - product detail view
- Store Inventory
  - store selector
  - inventory by store
  - low-stock/out-of-stock filters
- Availability Lookup
  - product selector
  - availability across stores
- Vector Recommendations
  - query text input
  - optional store selector
  - ranked recommendation results
  - display model/dimension/status next to results
- Integration Health
  - REST Source Catalog metadata
  - last refresh information where available
  - local endpoint links for the lab

## Implementation Tasks

- [ ] Generate initial APEXlang app source using Oracle's APEX skill workflow.
- [ ] Validate the generated source with SQLcl before import.
- [ ] Import into local APEX and verify pages render.
- [ ] Wire REST Source Catalog entries to the filtered OpenAPI artifact.
- [ ] Refine page labels, reports, and navigation for an operations-console
  workflow.
- [ ] Re-export and commit stable APEXlang source.

## Verification

Automated:

```bash
uv run python manage.py infra apex validate --alias cymbal-coffee-ops
make lint
```

Manual, when local APEX runtime is available:

```bash
make apex
uv run python manage.py infra apex import --alias cymbal-coffee-ops
# Open APEX and verify dashboard, products, stores, inventory, recommendations,
# and integration health pages.
uv run python manage.py infra apex export --app-id <app-id> --alias cymbal-coffee-ops
git diff -- src/apex/cymbal-coffee-ops
```

## Done

- APEX Operations Console source exists under `src/apex/cymbal-coffee-ops/`.
- The app imports and renders against the local APEX 26.1 + ORDS runtime.
- Pages demonstrate the same Cymbal Coffee product, store, inventory, vector,
  and model/status data as the Litestar app.
- SQLcl validation passes before import.

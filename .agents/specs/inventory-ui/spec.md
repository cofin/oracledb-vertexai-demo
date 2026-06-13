# Flow: inventory-ui

## Specification
The current UI allows exploring products and stores but doesn't show stock levels. This flow will add a "Live Inventory" view to the explore page or store detail view, using HTMX to load data dynamically.

### Requirements
*   Create a new Jinja partial template `_inventory_list.html.j2` in `src/app/domain/web/templates/partials/`.
*   Add an endpoint in `StoreController` at `/api/stores/{store_id:int}/inventory` to return the inventory partial or data.
*   Update the explore page or store detail view to include an HTMX trigger (`hx-get`) to load this inventory view.

### Code Analysis Summary
*   Templates are located in `src/app/domain/web/templates/`.
*   Controllers are in `src/app/domain/products/controllers/`. `_products.py` contains `StoreController`.
*   HTMX is used for dynamic loading.

## Implementation Plan

### Phase 1: Template Creation
- [ ] 1.1 Create `src/app/domain/web/templates/partials/_inventory_list.html.j2`.
- [ ] 1.2 The template should iterate over inventory items and display product name, quantity, and status.

### Phase 2: Controller Route
- [ ] 2.1 Add a new route to `StoreController` in `src/app/domain/products/controllers/_products.py`.
- [ ] 2.2 The route should fetch inventory for the given `store_id` and render the partial template.
- [ ] 2.3 Add a unit or integration test in `src/tests/api/test_store_inventory_route.py` to verify the route returns 200 and expected content.

### Phase 3: UI Integration
- [ ] 3.1 Modify `src/app/domain/web/templates/pages/explore.html.j2` or relevant partial to include a container for inventory.
- [ ] 3.2 Add an HTMX trigger to load the inventory when a store is selected or viewed.
- [ ] 3.3 Verify that inventory updates dynamically in the UI.

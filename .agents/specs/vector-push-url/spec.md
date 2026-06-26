# Flow: vector-push-url

## Specification

Update the URL pushed by the vector search demo endpoint to use `query` parameter instead of `q`. This ensures that when the user performs a search, the browser history is updated with the correct parameter name that matches what the explore page controller expects.

### Affected Files
- `src/app/domain/products/controllers/_vector.py`: Update `vector_search_demo` handler.
- `src/tests/integration/app/domain/products/controllers/test_vector_http.py`: Update tests to assert on `query` instead of `q` in pushed URL.

## Implementation Plan

### Phase 1: Update Controller and Tests

- [ ] **2.1 Update VectorController pushed URL** (`oracledb-vertexai-demo-oql.2.1`)
  - Modify `src/app/domain/products/controllers/_vector.py`
  - Change `push_url=f"/explore?q={quote(query)}"` to `push_url=f"/explore?query={quote(query)}"` in `vector_search_demo`.

- [ ] **2.2 Update vector HTTP integration tests** (`oracledb-vertexai-demo-oql.2.2`)
  - Modify `src/tests/integration/app/domain/products/controllers/test_vector_http.py`
  - Update `HX-Push-Url` assertions in `test_htmx_returns_partial_and_pushes_url` and `test_htmx_vector_search_route_through_test_client` to expect `/explore?query=...` instead of `/explore?q=...`.

- [ ] **2.3 Verify vector controller changes** (`oracledb-vertexai-demo-oql.2.3`)
  - Run the vector HTTP tests:
    ```bash
    pytest src/tests/integration/app/domain/products/controllers/test_vector_http.py
    ```

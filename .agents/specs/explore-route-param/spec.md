# Flow: explore-route-param

## Specification

We need to update the explore page route to accept `query` as the query parameter instead of `q`. This aligns with the form input name `query` and ensures that default form submissions (e.g. when hitting Enter) pre-fill the search input correctly on page reload.

### Affected Files
- `src/app/domain/web/controllers/_pages.py`: Update `explore_page` handler.
- `src/tests/integration/app/domain/web/controllers/test_pages.py`: Update tests to use `query` instead of `q`.

## Implementation Plan

### Phase 1: Update Controller and Tests

- [ ] **1.1 Update PageController.explore_page parameter** (`oracledb-vertexai-demo-oql.1.1`)
  - Modify `src/app/domain/web/controllers/_pages.py`
  - Change `q: FromQuery[str | None] = None` to `query: FromQuery[str | None] = None` in `explore_page` signature.
  - Ensure the template context still receives `query` (it already uses `query=q or ""`, so change to `query=query or ""`).

- [ ] **1.2 Update explore page integration tests** (`oracledb-vertexai-demo-oql.1.2`)
  - Modify `src/tests/integration/app/domain/web/controllers/test_pages.py`
  - Update `test_explore_page_prefills_shared_query` to call `/explore?query=dark%20roast` instead of `/explore?q=dark%20roast`.

- [ ] **1.3 Verify PageController changes** (`oracledb-vertexai-demo-oql.1.3`)
  - Run the page tests:
    ```bash
    pytest src/tests/integration/app/domain/web/controllers/test_pages.py
    ```

# Flow: explore-frontend-submit

## Specification

Update the explore page template to handle the form's `submit` event via HTMX. This will allow users to press Enter in the search input to trigger the search immediately, rather than waiting for the keyup delay, and will prevent the browser's default form submission which reloads the page.

### Affected Files
- `src/app/domain/web/templates/pages/explore.html.j2`: Update `search_trigger` variable.

## Implementation Plan

### Phase 1: Update Template and Verify

- [ ] **3.1 Update explore template search trigger** (`oracledb-vertexai-demo-oql.3.1`)
  - Modify `src/app/domain/web/templates/pages/explore.html.j2`
  - Change line 14:
    ```jinja2
    {% set search_trigger = "submit, load, keyup changed delay:300ms" if query else "submit, keyup changed delay:300ms" %}
    ```
    This adds `submit` as an alternative trigger. HTMX will now listen for `submit` on the form and handle it by performing the `hx-post` request and preventing default browser submission.

- [ ] **3.2 Verify manual search behavior** (`oracledb-vertexai-demo-oql.3.2`)
  - Start the application:
    ```bash
    uv run coffee run
    ```
  - Open browser to `http://localhost:8000/explore` (or the configured port).
  - Test the following scenarios:
    1. Type a query and wait. Verify search results and explain plan update after ~300ms.
    2. Type a query and immediately press Enter. Verify search results and explain plan update immediately without page reload.
    3. Verify that the URL changes to `/explore?query=your+query` (pushed URL).
    4. Copy the pushed URL, open in a new tab, and verify it loads the page pre-filled with the query and triggers the search on load.

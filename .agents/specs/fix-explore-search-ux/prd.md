# Master PRD: Fix Explore Search UX

## Context
On the explore page, typing a query triggers vector search and explain plan generation on key-up. However, hitting Enter clears or breaks the search. This is due to a mismatch between the query parameter expected by the page controller (`q`) and the form input name (`query`), combined with the lack of handling for the form's `submit` event in HTMX.

We will align everything to use `query` as the parameter name and configure HTMX to handle form submission, allowing the Enter key to trigger search immediately without a full page reload.

## Roadmap (Chapters)
1. **Chapter 1: Align Web Route Parameter** (`explore-route-param`)
   - Update `PageController.explore_page` to accept `query` parameter instead of `q`.
   - Update integration tests for the explore page.
2. **Chapter 2: Update Vector Controller Pushed URL** (`vector-push-url`)
   - Update `VectorController.vector_search_demo` to push `/explore?query=...` instead of `/explore?q=...`.
   - Update integration tests for the vector demo endpoint.
3. **Chapter 3: Enhance Frontend Search Form** (`explore-frontend-submit`)
   - Update `explore.html.j2` to use `submit` in `hx-trigger` for the search form.
   - Verify Enter key behavior.

## Global Constraints
- Keep `query` as the sole query parameter name for explore search.
- Ensure HTMX handles form submission to prevent default browser reloads.

# Master PRD: UI Regression Recovery

*PRD ID: `ui-regression-recovery_20260501`*
*Created: 2026-05-01*
*Status: Implemented*

---

## North Star

Recover the demo-quality UI that existed on `main` while keeping the ADK2,
SQLSpec, Litestar, HTMX, Alpine, Tailwind v4, and Vite rewrite direction. The
reference baseline is the `main` branch HTMX/Jinja application:

- `app/server/templates/coffee_chat.html`
- `app/server/templates/performance_dashboard.html`
- `app/server/templates/partials/_vector_results.html`
- `app/server/static/js/help-tooltips-htmx.js`
- `app/server/static/css/help-tooltips.css`
- `docs/screenshots/cymbal_chat.png`
- `docs/screenshots/performance_dashboard.png`

This is not a React restoration. React was an unfinished upgrade attempt and is
not the visual or behavioral baseline for this recovery.

---

## Current Problems

1. The chat UI is better than the first ADK2 rewrite, but it is still missing
   the richer `main` affordances: message-level metadata affordances, readable
   detail popovers, and clear per-phase timing context.
2. The explore page regressed from the older dashboard. It currently needs the
   core vector, explain, metrics, and chart/dashboard treatment restored while
   leaving the descoped classify-compare comparison out of the active UI.
3. SQL visibility has not been restored. The old UI explained the Oracle query
   path; the new UI shows query text and timings but not the SQL that ran.
4. The charts do not match the older dashboard quality. ApexCharts is present,
   but the current page does not provide the explanatory layout, polish, or
   interaction density users need for this demo.
5. Several older specs still referenced the pre-refactor test tree. New work
   must use the refactored `src/tests` module-path structure.

---

## Product Requirements

### Chat Experience

- Preserve streaming. The chat form must continue to use `/api/chat/stream` and
  progressively render deltas before the final payload lands.
- Every assistant message should show compact telemetry chips for:
  - intent classification
  - vector/RAG query text when a product lookup ran
  - total response runtime
  - embedding runtime
  - Oracle vector runtime
  - embedding-cache hit
  - response-cache hit
- Telemetry chips must open a detail popover or modal that explains the phase in
  user-understandable terms without exposing internal implementation noise.
- Product recommendations must stay menu-grounded. If the response is
  `PRODUCT_RAG`, the answer may recommend only products returned from the
  product search/detail tool payload.
- For non-SQL phases, the detail surface must say that no SQL was executed
  instead of inventing a fake query.

### Explore/Dashboard Experience

- Restore a four-panel explore/dashboard page:
  1. vector search
  2. EXPLAIN PLAN viewer
  3. metrics summary
  4. latency time-series chart
- Use the `main` HTMX dashboard and screenshots as the visual reference:
  readable metric cards, clear chart groupings, restrained Cymbal Coffee
  branding, and helpful detail affordances.
- ApexCharts is acceptable, but the resulting page must be visually comparable
  to the old dashboard. If ApexCharts cannot reproduce the quality quickly,
  switch the implementation detail rather than accepting a worse chart.

### Executed SQL Visibility

Executed SQL detail is a first-class requirement, not a debug afterthought.
Every SQL-backed phase shown in chat or explore must expose:

- named SQL key
- rendered SQL text that was executed
- safe bind summary
- row count/result count
- phase runtime
- cache status where relevant

The bind summary must not dump raw 3072-dimensional vectors. Vector binds should
be summarized as a redacted/vector descriptor, for example:

```text
query_vector=<VECTOR[3072 FLOAT32], sha256=..., norm=...>
threshold=0.5
limit=5
```

Required SQL surfaces:

- Chat product RAG: `vector-search-products`, with vector bind summary and
  product row count.
- Chat response cache: `get-cached-response`, with cache key redacted or hashed.
- Chat embedding cache: `get-cached-embedding`, with text hash and model.
- Explore vector search: `vector-search-products`.
- Explore EXPLAIN PLAN: `explain-plan-vector-search` and
  `explain-plan-display`.
- Metrics summary/charts: `get-performance-stats`, `get-cache-stats`, and
  `metrics-time-series`.

### Test Layout Alignment

All new or updated tests must follow the refactored layout documented in
`src/tests/README.md`.

| Behavior | Test home |
|---|---|
| Chat HTTP and SSE contracts | `src/tests/integration/app/domain/chat/controllers/test_chat_http.py` |
| Chat ADK/service behavior | `src/tests/unit/app/domain/chat/services/test_adk.py` and `src/tests/integration/app/domain/chat/services/test_chat_workflow.py` |
| Chat frontend JS contracts | `src/tests/unit/src/resources/test_chat_frontend.py` |
| Explore page rendering | `src/tests/integration/app/domain/web/controllers/test_pages.py` |
| Vector demo HTTP/HTMX contracts | `src/tests/integration/app/domain/products/controllers/test_vector_http.py` |
| Vector/explain controller unit contracts | `src/tests/unit/app/domain/products/controllers/test_vector.py` and `src/tests/unit/app/domain/products/controllers/test_explain_plan.py` |
| Metrics chart/summary schema contracts | `src/tests/unit/app/domain/system/controllers/test_metrics_charts.py` and `src/tests/unit/app/domain/system/controllers/test_metrics_summary_cards.py` |
| Named SQL registry and SQL call-site coverage | `src/tests/unit/app/db/test_named_sql.py` |

Do not add `src/tests/api`, direct `src/tests/unit/test_*.py`, direct
`src/tests/integration/test_*.py`, or issue-named regression buckets.

---

## Roadmap

### Chapter 1 - `ui-reference-audit_20260501`

Compare the current branch against `main` and the screenshots before changing
the UI.

Deliverables:

- Capture the current branch chat and explore screenshots.
- Inspect `main` HTMX/Jinja templates, static JS/CSS, and screenshots.
- Produce a short checklist of visual/behavioral gaps for chat, explore, charts,
  popovers, and SQL visibility.

Acceptance:

- The implementation checklist explicitly names the `main` HTMX/Jinja files used
  as reference.
- The checklist does not mention React as the baseline.

### Chapter 2 - `chat-telemetry-recovery_20260501`

Restore rich chat telemetry while preserving ADK2 streaming.

Deliverables:

- Extend the final SSE payload with structured telemetry for intent, lookup
  query, timings, cache hits, row counts, and SQL phase details.
- Render message-level telemetry chips and detail popovers for streamed and
  non-streamed responses.
- Ensure cached responses still show the original product lookup telemetry and
  indicate response-cache hit.

Tests:

- Extend `src/tests/integration/app/domain/chat/controllers/test_chat_http.py`
  for SSE final telemetry and cache-hit metadata.
- Extend `src/tests/unit/src/resources/test_chat_frontend.py` for popover/detail
  rendering source contracts.
- Extend `src/tests/unit/app/domain/chat/services/test_adk.py` for typed
  telemetry payload shape.

Acceptance:

- Streaming remains enabled.
- A product-RAG chat turn visibly shows intent, query, timing, embedding-cache,
  response-cache, and SQL detail affordances.
- No invented menu products are shown.

### Chapter 3 - `explore-dashboard-recovery_20260501`

Restore the old dashboard quality on the current HTMX/Vite stack.

Deliverables:

- Rework `pages/explore.html.j2` to render the core four panels.
- Improve chart styling/layout to match the old dashboard quality.
- Add result/detail popovers for vector search and EXPLAIN PLAN output.

Tests:

- Extend `src/tests/integration/app/domain/web/controllers/test_pages.py` so
  `/explore` requires the core panel IDs and excludes descoped compare UI.
- Extend `src/tests/integration/app/domain/products/controllers/test_vector_http.py`
  for vector-result telemetry/detail payload.
- Extend `src/tests/unit/src/resources/test_chat_frontend.py` or add
  `src/tests/unit/src/resources/test_explore_frontend.py` for chart/popover JS
  contracts.

Acceptance:

- `/explore` renders the four in-scope visible panels.
- Charts are readable at desktop and mobile widths.
- The descoped classify-compare panel and endpoint are absent.

### Chapter 4 - `executed-sql-visibility_20260501`

Create a safe, typed telemetry path for executed SQL.

Deliverables:

- Add a shared schema for SQL phase telemetry, likely under
  `app.domain.system.schemas` or a narrow chat/products schema if ownership is
  clearer after implementation research.
- Capture named SQL keys and rendered SQL text at the service boundary where the
  query is executed.
- Redact vector and cache-key binds while preserving useful shape information.
- Render SQL in chat/explore popovers with copyable formatting.

Tests:

- Extend `src/tests/unit/app/db/test_named_sql.py` so newly surfaced SQL keys are
  registry-backed.
- Add/extend service tests in the module path where telemetry is produced.
- Extend HTTP tests to assert SQL telemetry is present for SQL-backed phases and
  absent-with-explanation for non-SQL phases.

Acceptance:

- Users can see the actual SQL that was executed for SQL-backed phases.
- No raw embeddings or sensitive cache/session identifiers are printed.
- Every displayed SQL string maps to a real named SQL key.

### Chapter 5 - `ui-regression-verification_20260501`

Lock in the restored behavior.

Deliverables:

- Run focused unit/integration tests for the changed modules.
- Run frontend type/build checks.
- Capture Playwright screenshots for chat and explore.
- Compare against `docs/screenshots/cymbal_chat.png` and
  `docs/screenshots/performance_dashboard.png`.

Acceptance:

- `make test` and `make lint` pass, or any unrelated failures are documented
  with exact evidence.
- Screenshots show restored chat telemetry and four-panel explore/dashboard.
- No stale `src/tests/api` paths are introduced.

---

## Out of Scope

- Restoring React or TanStack.
- Reintroducing legacy intent exemplars as the runtime classifier.
- Reintroducing classify-compare UI/API surfaces.
- Changing Oracle migrations except where needed for telemetry persistence.
- Running destructive demo/tape workflows.

---

## PRD Acceptance

This PRD is complete when:

- Chat telemetry and SQL detail affordances are visible and tested.
- Product recommendations remain menu-grounded.
- Explore renders the four in-scope panels and omits classify-compare.
- Metrics/charts look comparable to the `main` dashboard screenshots.
- Executed SQL is shown safely for SQL-backed phases.
- All tests live in the refactored module-path layout.

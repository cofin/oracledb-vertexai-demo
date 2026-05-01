# Learnings: UI Regression Recovery

## 2026-05-01 04:25 - Phase 1: Visual Baseline and Shared Shell

- **Implemented:** Restored a shared Cymbal Coffee app shell/header and reusable frontend primitives for panels, metric cards, telemetry chips, icon buttons, chart hosts, and popover surfaces.
- **Files changed:** `src/app/domain/web/templates/base.html.j2`, `_nav.html.j2`, `pages/chat.html.j2`, `pages/explore.html.j2`, `src/resources/main.js`, `src/resources/styles.css`, `src/tests/integration/app/domain/web/controllers/test_pages.py`, `src/tests/unit/src/resources/test_styles.py`.
- **Validation:** Red-phase focused tests failed before implementation; after implementation, focused page/resource tests passed, `./node_modules/.bin/vite build` passed, `make frontend-typecheck` passed, `make test` passed with 206 tests, and `make lint` passed cleanly.
- **Learning:** The current user-facing product/version label is `Oracle 26ai`, even though older reference screenshots and some planning language may mention `Oracle 23ai`.

## 2026-05-01 04:47 - Phase 2: Chat Instrumentation and Popovers

- **Implemented:** Added structured `sql_phases` telemetry to chat stream/final payloads, including response-cache lookup, embedding-cache lookup, and Oracle vector-search phases with named SQL keys, SQL text, sanitized binds, row counts, runtimes, and cache status.
- **Files changed:** `src/app/domain/chat/services/adk.py`, `src/app/domain/chat/controllers/_chat.py`, `src/app/domain/chat/schemas/_chat.py`, `src/resources/main.js`, and existing chat controller/service/frontend tests.
- **Validation:** Targeted chat/service/frontend tests passed, `./node_modules/.bin/vite build` passed, `make test` passed with 206 tests, and `make lint` passed cleanly.
- **Learning:** Store only product lookup SQL phases in cached response payloads; add a fresh `get-cached-response` phase at read time so cached turns show both the cache hit and the original product lookup context without preserving an old cache-miss phase.

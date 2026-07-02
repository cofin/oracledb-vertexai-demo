# Frontend & UI Development Guide

This guide details the Cymbal Coffee frontend stack, HTMX integration, Vite asset pipeline, and UI/UX conventions.

## Frontend Stack

- **Framework:** HTMX 2.x + Jinja2 templates (no React, no client-side SPA routing).
- **Styling:** Tailwind CSS v4.
- **Vite Integration:** Served via `litestar-vite` plugin in template mode.
- **Charts:** ApexCharts for performance and search telemetry.

## Asset Directory Layout

The Vite/npm project root is flatly separated under `src/resources/`.
- `src/resources/package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `public/`, and `node_modules/` live here.
- Python `ViteConfig.paths.root` must point directly to `src/resources/`.
- Do not run npm or Vite commands in the root of the project.
- Frontend TypeScript compiler (`tsc`) is checked during linting. If `tsc` is missing, install the frontend assets first:
  ```bash
  uv run python manage.py assets install
  ```

## HTMX Integration Patterns

Templates reside in `src/app/domain/web/templates/`.
- **Partials:** Smaller Jinja templates (e.g., `partials/message.html.j2`) handle HTMX swaps.
- **Form Interception:** The chat form captures `FormData` before applying any disabled/busy states. Disabling inputs before capturing form data removes them from the payload, which causes empty message errors.
- **HTMX Form Submission:** Avoid direct `hx-post` on forms when custom JS needs to handle SSE streams; instead, handle form submission and fetch the stream reader in JS.
- **`hx-ext="litestar"`:** Scope this extension carefully. Use it only on JSON-templating panels, and exclude it (using `ignore:litestar`) on partial HTML swap surfaces to prevent it from intercepting HTML responses.

## Vanilla JavaScript Widgets (Client-Only)

Educational calculators (e.g. Vector storage estimator) remain client-only to ensure high performance and avoid server round-trips.
- Keep them as vanilla JS modules under `src/resources/*.js`.
- Bind JS code to Jinja markup using HTML5 `data-*` attributes.
- Alpine.js is explicitly removed from the stack.

## Chat SSE Streaming

Streaming uses Server-Sent Events (SSE) manually processed via browser JavaScript:
- JS reads the `/api/chat/stream` response body using `fetch()` and a `ReadableStream` reader.
- It parses SSE text blocks (`data: ...`) and renders incremental model deltas in the chat bubble.
- Product RAG turns do not stream model deltas; they return a single final event. The browser UI displays a loading indicator until the grounded RAG payload is received.

## Telemetry & Dashboards

The `/explore` page displays search telemetry:
- **ApexCharts:** Renders SQL phase timing breakdowns (embedding latency, Oracle database query latency, etc.).
- **Telemetry Badges:** The chat UI shows message-level badges indicating:
  - Cache hits (response cache vs embedding cache).
  - Intent classification output.
  - Phase timings (ms).
- Timings must be extracted from the structured `search_metrics` payload returned by the final SSE event.

## Mobile UX Guidelines

- **Touch Targets:** Buttons and interactive elements must have a minimum size of 44x44px to remain easily tapable on mobile.
- **Font Sizes:** Input fields must use at least 16px font size to prevent iOS Safari from auto-zooming on focus.
- **Layouts:** Use Tailwind's responsive breakpoints (`sm:`, `md:`, `lg:`) to ensure cards, sidebar, and chat bubbles fit mobile screens comfortably.
- **Testing:** Debug using Safari Developer Tools or Chrome DevTools mobile emulation.

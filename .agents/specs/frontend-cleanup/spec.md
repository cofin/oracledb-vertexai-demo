# Flow: frontend-cleanup

*Beads: oracledb-vertexai-mzm.9 — CLOSED [09a426d]*

## Specification

Reduce frontend duplication and split the `main.js` monolith into focused ES
modules behind a thin bootstrap, without changing rendered behavior (except the
new "Get directions" link introduced by Ch7). De-duplicate the chat welcome
markup, contain the EXPLAIN-PLAN double-implementation hazard, loop-drive the
explore presets, tidy the flash color logic, and flatten redundant wrappers.

Depends on Ch5 (`oracledb-vertexai-mzm.5`, chat-path-consolidation — dead
partials removed) and Ch7 (`oracledb-vertexai-mzm.7`, maps-consolidation — the
`directions` action and its render path exist). Do this flow AFTER both land so
the welcome-markup and store-card surfaces are stable.

### Requirements

- No duplicated chat welcome markup: one source of truth shared between the
  server-rendered initial state and the JS reset path.
- `main.js` split into `chat-stream.js`, `telemetry.js`, `charts.js`,
  `geolocation.js`, and a thin `main.js` bootstrap that imports them. The single
  Vite input stays `main.js`; modules are pulled in via ES `import`.
- Explore model presets driven by a Jinja `{% for %}` loop over a preset list.
- Flash category color resolved via a `{% set %}` map, not nested ternaries.
- EXPLAIN-PLAN duplication hazard reduced with the pragmatic minimal change (a
  documented shared column/row contract), not a risky shared-renderer rewrite.
- Rendered UI unchanged except the Ch7 directions link.
- Built assets under `src/app/domain/web/static/assets/main-*.js` and
  `styles-*.css` are GENERATED — never hand-edit; the build regenerates them.

### Code Analysis Summary

- Welcome markup duplicated:
  - `src/app/domain/web/templates/pages/chat.html.j2:56-67` — server-rendered
    initial AI message (avatar "B", "Barista", "READY" chip, "Tell me what sounds
    good and I'll check the Cymbal Coffee menu.").
  - `src/resources/main.js:56-67` — `welcomeMessageHtml()` returns the same block
    (one chip text difference: template shows "READY", JS omits it). Used by
    `resetChatMessages()` (`:69-81`) which sets `messages.innerHTML`.
- EXPLAIN PLAN double implementation (both live, different surfaces):
  - `src/resources/main.js:179-241` — `renderPlanRows` (`:179`) +
    `renderExplainPlan` (`:222`); JS-built table for the chat telemetry popover.
  - `src/app/domain/web/templates/partials/plan_lines.html.j2:18-59` — Jinja
    table for the explore page. Same column contract: Id, Operation, Name, Rows,
    Cost, Time; same `is_vector` row highlight; same colgroup widths; same "Raw
    DBMS_XPLAN output" `<details>`.
- `main.js` (~1029 LOC) responsibilities to split:
  - chat stream: SSE parsing + chat submit/clear/reset (`parseSseBlock` `:860`,
    `readEventStream` `:908`, `handleChatStreamEvent` `:883`, submit handler
    `:937`, append/pending helpers `:790-858`, `resetChatMessages` `:69`,
    `welcomeMessageHtml` `:56`, store-card rendering `:655-788`).
  - telemetry: chips, SQL-phase render, EXPLAIN plan, popover (`renderMetrics`
    `:89`, `telemetryChip` `:132`, `renderSqlPhase` `:151`, `renderPlanRows`
    `:179`, `renderExplainPlan` `:222`, `loadExplainPlan` `:243`,
    `showTelemetryPopover` `:264`, `hideTelemetryPopover` `:314`,
    `renderMessageTelemetry` `:326`).
  - charts: `renderEmptyChart` `:550`, `initDashboardCharts` `:558` (ApexCharts).
  - geolocation: `GEOLOCATION_OPTIONS` `:35`, `chatLocationState` `:41`,
    location field helpers `:436-486`, `requestBrowserLocation` `:488`.
  - bootstrap: shared utils (`escapeHtml` `:27`, `onReady` `:19`, `processHtmxDom`
    `:13`, `scrollMessages` `:45`), htmx/ApexCharts globals (`:9-11`),
    `initPersonaPicker` `:535`, the body `submit`/`click` delegated listeners
    (`:937`, `:983`), and the `onReady(...)` init (`:1023`). Imports
    `initVectorCalculator` from `./vector-calculator.js` (`:7`) — existing
    proof that ES-module splitting is already in use.
- `src/resources/vite.config.ts:18` — `input: ["main.js", "styles.css"]`. Single
  JS entry; ES imports from `main.js` keep that single input (no config change
  needed; `vector-calculator.js` already follows this pattern).
- Explore presets: `pages/explore.html.j2:122-143` — FIVE hand-written buttons:
  Gemini 768, Gemini 3072, OpenAI 1536, Cohere 1024, Cohere 4096. NOTE: the PRD
  text references a duplicate "OpenAI 3072" preset; it does NOT exist in current
  code, so there is nothing to drop — loop-drive the five real presets as-is.
  Each button has `data-vector-preset`, `data-preset-dimensions`,
  `data-preset-format="FLOAT32"`.
- Class conflict: `explore.html.j2:124` (repeated per button) has
  `text-xs font-semibold text-base` — `text-xs` and `text-base` are conflicting
  font-size utilities. Keep one (`text-xs`).
- Empty wrapper: `explore.html.j2:110-116` — the calculator header's `<div
  class="flex ... justify-between ...">` wraps a single title block plus an empty
  trailing region (the second flex child was removed); flatten if it has one
  child.
- Flash colors: `partials/_flash.html.j2:9` — triple-nested ternary choosing
  `success`/`danger`/`accent-strong`/`muted` from `f.category`.
- Sidebar wrappers: `pages/chat.html.j2:16-21` — `<div class="space-y-5">`
  wrapping a single `<div>` (the kicker + heading); redundant single-child nest.

### EXPLAIN-PLAN hazard: chosen minimal approach

Both renderers are live on different surfaces (JS popover vs Jinja partial) and
consume the same plan shape with the same six columns. A shared renderer would
require unifying a server template and a client string builder — risky for no
behavior gain. Pragmatic minimal task: add a short behavior-only comment at the
top of BOTH `renderPlanRows` (main.js) and the `plan_lines.html.j2` table
documenting the shared column/row contract (Id, Operation, Name, Rows, Cost,
Time; `is_vector` highlight) so the two stay in lockstep. Do not extract a shared
renderer in this flow.

## Implementation Plan

### Phase 1: De-duplicate the welcome markup
- [x] 1.1 Choose template as the single source: keep the server-rendered welcome
      block in `chat.html.j2:56-67` (it is the canonical initial state).
- [x] 1.2 In `main.js`, change `resetChatMessages` (`:69-81`) to clone the
      server welcome node instead of injecting `welcomeMessageHtml()`. Approach:
      wrap the template welcome block in a hidden `<template data-chat-welcome>`
      (or read the first `.message-row-ai` rendered when history is empty) and set
      `messages.innerHTML = template.innerHTML`. Delete `welcomeMessageHtml`
      (`:56-67`). Reconcile the one text difference by keeping the template's
      "READY" chip as the single rendered version.
- [x] 1.3 Verify reset still clears `metrics-badges`, hides the telemetry popover,
      clears the chat error, and scrolls (existing `resetChatMessages` body).

### Phase 2: Split main.js into modules + bootstrap
- [x] 2.1 Create `src/resources/geolocation.js`: move `GEOLOCATION_OPTIONS`,
      `chatLocationState`, the location-field helpers (`:436-486`), and
      `requestBrowserLocation` (`:488`). Export `requestBrowserLocation` (and any
      state the submit path reads).
- [x] 2.2 Create `src/resources/charts.js`: move `renderEmptyChart` (`:550`) and
      `initDashboardCharts` (`:558`). Export `initDashboardCharts`. Import
      `ApexCharts` in this module (drop the `window.ApexCharts` global if nothing
      else needs it; keep it only if other code references `window.ApexCharts`).
- [x] 2.3 Create `src/resources/telemetry.js`: move the telemetry/plan/popover
      block (`renderMetrics`, `telemetryChip`, `renderSqlPhase`, `renderPlanRows`,
      `renderExplainPlan`, `loadExplainPlan`, `showTelemetryPopover`,
      `hideTelemetryPopover`, `renderMessageTelemetry`, and their small helpers
      `formatMetricMs`/`payloadSqlPhases`/`phasesFor`/`telemetryDetail`/
      `planValue`/`encodeDetail`). Export what chat-stream + bootstrap call
      (`renderMessageTelemetry`, `renderMetrics`, `hideTelemetryPopover`,
      `showTelemetryPopover`). Import shared `escapeHtml` from the bootstrap/util
      module.
- [x] 2.4 Create `src/resources/chat-stream.js`: move SSE parsing + chat lifecycle
      (`parseSseBlock`, `readEventStream`, `handleChatStreamEvent`, the
      append/pending/finalize helpers `:790-858`, `resetChatMessages`, the
      store-card renderers `:655-788`, `showChatError`/`clearChatError`,
      `announceToScreenReader`). It imports telemetry render functions from
      `telemetry.js`. Export the chat submit handler and reset/clear handlers used
      by the delegated listeners.
- [x] 2.5 Reduce `main.js` to a bootstrap: keep shared utils (`escapeHtml`,
      `onReady`, `processHtmxDom`, `scrollMessages`) — either inline or in a small
      `util.js` imported by the modules — plus htmx registration (`:4-11`),
      `initPersonaPicker`, the body `submit`/`click` delegated listeners wired to
      the imported handlers, and the `onReady(...)` init calling `processHtmxDom`,
      `initPersonaPicker`, `initDashboardCharts` (charts.js), `initVectorCalculator`,
      `scrollMessages`. Keep the existing `import { initVectorCalculator } from
      "./vector-calculator.js"`.
- [x] 2.6 Resolve shared `escapeHtml`/`scrollMessages` by exporting from one place
      (e.g. `util.js`) and importing where needed; avoid duplicating them across
      modules.
- [x] 2.7 Do not touch `vite.config.ts` — `main.js` remains the single JS input;
      modules load via ES imports. Do not hand-edit generated `static/assets/*`.

### Phase 3: EXPLAIN-PLAN contract note
- [x] 3.1 Add a behavior-only comment above `renderPlanRows` (`main.js:179`) and
      above the `plan_lines.html.j2` table (`:18`) documenting the shared six-column
      contract (Id, Operation, Name, Rows, Cost, Time) and the `is_vector` row
      highlight, noting the two renderers must stay aligned. No code extraction.
      (Comment must describe behavior only — no spec/phase/PRD references.)

### Phase 4: Explore presets loop + class/wrapper fixes
- [x] 4.1 In `explore.html.j2`, define a preset list (e.g. a `{% set presets = [...] %}`
      of `{label, dimensions, format}` for the five real presets: Gemini 768 /
      Gemini 3072 / OpenAI 1536 / Cohere 1024 / Cohere 4096) and render the buttons
      with `{% for p in presets %}`, emitting `data-vector-preset`,
      `data-preset-dimensions="{{ p.dimensions }}"`, `data-preset-format="{{ p.format }}"`,
      and `{{ p.label }}`. (No duplicate preset exists to drop — the PRD's "OpenAI
      3072" is not in the code.)
- [x] 4.2 Fix the font-size conflict in the button class (`:124`): drop `text-base`,
      keep `text-xs font-semibold` (apply once via the loop).
- [x] 4.3 Flatten the empty calculator-header flex wrapper (`:110-116`): if it has a
      single child after the trailing region removal, drop the wrapper and keep the
      title/description block directly.

### Phase 5: Flash color map + sidebar flatten
- [x] 5.1 In `_flash.html.j2`, replace the nested ternary (`:9`) with a `{% set
      flash_colors = {"success": "success", "error": "danger", "warning":
      "accent-strong"} %}` and use `flash_colors.get(f.category, "muted")` for the
      `text-*` class.
- [x] 5.2 In `chat.html.j2`, flatten the redundant single-child sidebar wrapper
      (`:16-21`): drop the `<div class="space-y-5">` that wraps only the kicker +
      heading `<div>`, keeping the inner block directly.

### Phase 6: Build + smoke
- [x] 6.1 `cd src/resources && npm run build` succeeds (modules bundle behind the
      single `main.js` input; generated assets regenerate).
- [x] 6.2 `uv run pytest src/tests/integration/app/domain/web/controllers/test_pages.py`
      passes (chat + explore page smoke).
- [x] 6.3 `make lint` and `make test` green.

## Acceptance

- [x] No duplicated welcome markup: `welcomeMessageHtml` removed; reset clones the
      server-rendered welcome block.
- [x] `main.js` split into `chat-stream.js`, `telemetry.js`, `charts.js`,
      `geolocation.js`, plus a thin `main.js` bootstrap importing them; single Vite
      input unchanged.
- [x] Explore presets render from a Jinja loop; `text-base` conflict removed; empty
      calculator-header wrapper flattened.
- [x] Flash colors come from a `{% set %}` map; redundant chat sidebar wrapper
      flattened.
- [x] EXPLAIN-PLAN column/row contract documented on both renderers (no risky
      rewrite).
- [x] `npm run build` and `test_pages.py` page smoke pass; rendered UI unchanged
      except the Ch7 "Get directions" link.

## Verification

```bash
grep -n "welcomeMessageHtml" src/resources/*.js               # expect: no matches
ls src/resources/chat-stream.js src/resources/telemetry.js \
   src/resources/charts.js src/resources/geolocation.js
grep -n "input:" src/resources/vite.config.ts                 # still ["main.js","styles.css"]
cd src/resources && npm run build
uv run pytest src/tests/integration/app/domain/web/controllers/test_pages.py
make lint
make test
```

# Learnings: frontend-cleanup

Synced from Beads epic `oracledb-vertexai-mzm.9` (CLOSED, commit `09a426d`).

## Welcome-markup source of truth

`chat.html.j2` is canonical. A Jinja `{% macro chat_welcome() %}` renders the
welcome block both in the empty-history branch (the visible initial state) and
inside a hidden `<template data-chat-welcome>`. The JS reset path
(`resetChatMessages`) clones `template.innerHTML` instead of the old
`welcomeMessageHtml()` string builder, which is deleted. The single "READY" chip
from the template is the one rendered version.

## main.js module split

`main.js` split into ES modules behind the single Vite `main.js` input (no
`vite.config.ts` change — modules load via ES `import`, the same pattern
`vector-calculator.js` already used):

- `util.js` — `escapeHtml`, `encodeDetail`, `onReady`, `processHtmxDom`,
  `scrollMessages`.
- `geolocation.js` — `requestBrowserLocation` plus location field/state helpers.
- `charts.js` — `initDashboardCharts` and `renderEmptyChart`; imports
  `ApexCharts` directly. The `window.ApexCharts` global was dropped because
  nothing read it (`window.htmx` stays — the htmx extension needs it).
- `telemetry.js` — `renderMetrics`, `renderMessageTelemetry`,
  `showTelemetryPopover`/`hideTelemetryPopover`, `renderPlanRows`,
  `renderExplainPlan`, `loadExplainPlan`, plus chip/SQL-phase helpers. Carries
  the EXPLAIN-PLAN column/row contract comment.
- `chat-stream.js` — SSE parse/read, `handleChatSubmit`/`handleClearChat`,
  store-card renderers, and `resetChatMessages` (clones the welcome template).
- `main.js` — thin bootstrap: htmx global + extension registration,
  `initPersonaPicker`, delegated `submit`/`click` listeners, `onReady` init.

Nothing was deliberately left coupled in `main.js` beyond the persona picker and
the delegated listeners; the chat-stream code split cleanly via exported
handlers.

## EXPLAIN-PLAN duplication

Two live renderers (JS popover via `renderPlanRows`, Jinja
`plan_lines.html.j2`) share a six-column contract (Id, Operation, Name, Rows,
Cost, Time) with an `is_vector` row highlight. A behavior-only comment was added
above both renderers so they stay aligned; no shared-renderer extraction (the
risk outweighed any behavior gain).

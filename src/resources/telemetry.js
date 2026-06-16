// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import { encodeDetail, escapeHtml } from "./util.js"

export const renderMetrics = (payload) => {
  const target = document.getElementById("metrics-badges")
  if (!target) {
    return
  }
  const metrics = payload.search_metrics ?? {}
  const vectorQuery = metrics.vector_query ?? metrics.query
  const badges = [
    ["Intent", payload.intent_detected],
    ["Query", vectorQuery],
    ["Total", Number.isFinite(metrics.total_ms) ? `${metrics.total_ms} ms` : null],
    ["Oracle", Number.isFinite(metrics.oracle_ms) ? `${metrics.oracle_ms} ms` : null],
    ["Embedding", Number.isFinite(metrics.embedding_ms) ? `${metrics.embedding_ms} ms` : null],
    ["Embedding cache", payload.embedding_cache_hit ? "Hit" : null],
    ["Source", payload.from_cache ? "Response cache" : "Live"],
  ].filter(([, value]) => value)

  target.innerHTML = badges
    .map(
      ([label, value]) =>
        `<span class="telemetry-chip border-accent/20 bg-accent-soft text-accent-strong" data-telemetry-chip>${label}: ${escapeHtml(String(value))}</span>`,
    )
    .join("")
}

const formatMetricMs = (value) => {
  if (!Number.isFinite(value)) {
    return null
  }
  return `${Math.round(value)} ms`
}

const payloadSqlPhases = (payload) => (Array.isArray(payload.sql_phases) ? payload.sql_phases : [])

const phasesFor = (payload, sqlKey) => payloadSqlPhases(payload).filter((phase) => phase.sql_key === sqlKey)

const telemetryDetail = (title, summary, sqlPhases = [], options = {}) => ({
  title,
  summary,
  sqlPhases,
  ...options,
})

const telemetryChip = (icon, label, value, variant = "neutral", detail = null) => {
  const variantClass =
    variant === "hit"
      ? "border-success/25 bg-success/10 text-success"
      : "border-border bg-surface-strong/55 text-muted"
  const content = `
    <span class="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-surface text-[10px] font-semibold text-accent-strong" aria-hidden="true">${icon}</span>
    <span class="truncate">${escapeHtml(String(value))}</span>
  `
  if (!detail) {
    return `<span class="telemetry-chip ${variantClass}" data-telemetry-chip title="${escapeHtml(
      `${label}: ${value}`,
    )}">${content}</span>`
  }
  return `<button type="button" class="telemetry-chip ${variantClass}" data-telemetry-chip data-telemetry-detail="${encodeDetail(
    detail,
  )}" aria-label="${escapeHtml(`${label}: ${value}`)}">${content}</button>`
}

const renderSqlPhase = (phase) => {
  const binds = Object.entries(phase.binds ?? {})
    .map(
      ([key, value]) =>
        `<div class="flex items-center justify-between gap-2 text-xs"><span class="text-muted">${escapeHtml(key)}</span><span class="font-mono text-strong">${escapeHtml(
          String(value),
        )}</span></div>`,
    )
    .join("")
  return `<section class="mt-3 rounded-lg border border-border bg-surface-strong/60 p-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="text-sm font-semibold text-strong">${escapeHtml(phase.label ?? "SQL phase")}</h3>
      <span class="font-mono text-xs text-muted">${escapeHtml(phase.sql_key ?? "unknown")}</span>
    </div>
    <div class="mt-2 grid grid-cols-3 gap-2 text-xs text-muted">
      <span>${Number.isFinite(phase.runtime_ms) ? `${Math.round(phase.runtime_ms)} ms` : "runtime n/a"}</span>
      <span>${Number.isFinite(phase.row_count) ? `${phase.row_count} rows` : "rows n/a"}</span>
      <span>${escapeHtml(phase.cache_status ?? "cache n/a")}</span>
    </div>
    <pre class="mt-3 max-h-48 overflow-auto rounded-md bg-deep p-3 text-xs leading-relaxed text-white"><code>${escapeHtml(
      phase.sql ?? "No SQL text recorded.",
    )}</code></pre>
    <div class="mt-3 space-y-1">${binds || '<p class="text-xs text-muted">No binds recorded.</p>'}</div>
  </section>`
}

const planValue = (plan, camelKey, snakeKey, fallback = null) => plan?.[camelKey] ?? plan?.[snakeKey] ?? fallback

// Plan table contract: six columns in order — Id, Operation, Name, Rows, Cost,
// Time — with rows flagged isVector/is_vector highlighted (bg-accent-soft/60
// text-accent-strong). The explore page renders an identical table server-side
// from the same plan shape; both renderers must keep the same columns and
// highlight.
const renderPlanRows = (rows) => {
  if (!Array.isArray(rows) || rows.length === 0) {
    return ""
  }
  const body = rows
    .map((row) => {
      const isVector = Boolean(row.isVector ?? row.is_vector)
      const rowClass = isVector ? "bg-accent-soft/60 text-accent-strong" : "text-strong"
      return `<tr class="border-t border-border ${rowClass}">
        <td class="px-3 py-2 font-mono">${escapeHtml(String(row.id ?? ""))}</td>
        <td class="break-words px-3 py-2 font-medium">${escapeHtml(String(row.operation ?? ""))}</td>
        <td class="break-words px-3 py-2 font-mono text-muted">${escapeHtml(String(row.name || "-"))}</td>
        <td class="px-3 py-2 text-right font-mono text-muted">${escapeHtml(String(row.rows || "-"))}</td>
        <td class="break-words px-3 py-2 text-right font-mono text-muted">${escapeHtml(String(row.cost || "-"))}</td>
        <td class="break-words px-3 py-2 text-right font-mono text-muted">${escapeHtml(String(row.time || "-"))}</td>
      </tr>`
    })
    .join("")
  return `<div class="mt-3 overflow-auto border-y border-border bg-surface/45">
    <table class="w-full table-fixed text-left text-xs">
      <colgroup>
        <col class="w-10">
        <col>
        <col class="w-24">
        <col class="w-16">
        <col class="w-20">
        <col class="w-20">
      </colgroup>
      <thead class="bg-surface-strong text-muted">
        <tr>
          <th class="px-3 py-2 font-semibold">Id</th>
          <th class="px-3 py-2 font-semibold">Operation</th>
          <th class="px-3 py-2 font-semibold">Name</th>
          <th class="px-3 py-2 text-right font-semibold">Rows</th>
          <th class="px-3 py-2 text-right font-semibold">Cost</th>
          <th class="px-3 py-2 text-right font-semibold">Time</th>
        </tr>
      </thead>
      <tbody>${body}</tbody>
    </table>
  </div>`
}

const renderExplainPlan = (plan) => {
  const summary = String(planValue(plan, "planSummary", "plan_summary", "Plan unavailable") || "Plan unavailable")
  const lines = planValue(plan, "planLines", "plan_lines", [])
  const rows = planValue(plan, "planRows", "plan_rows", [])
  if (summary === "Plan unavailable") {
    const message = Array.isArray(lines) && lines.length ? lines[0] : "Plan unavailable."
    return `<p class="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger" role="alert">${escapeHtml(
      String(message),
    )}</p>`
  }
  const rawLines = Array.isArray(lines) ? lines.join("\n") : ""
  return `<div class="space-y-3">
    <p class="text-xs text-muted">Top vector op: <span class="font-mono text-accent-strong">${escapeHtml(summary)}</span></p>
    ${renderPlanRows(rows)}
    <details class="border-b border-border bg-deep">
      <summary class="cursor-pointer px-3 py-2 text-xs font-semibold text-surface/80">Raw DBMS_XPLAN output</summary>
      <pre class="max-h-48 overflow-auto border-t border-border p-3 font-mono text-xs leading-relaxed text-surface">${escapeHtml(rawLines)}</pre>
    </details>
  </div>`
}

const loadExplainPlan = async (query) => {
  const host = document.querySelector("[data-explain-plan-host]")
  if (!(host instanceof HTMLElement)) {
    return
  }
  try {
    const response = await fetch(`/api/explain-plan?query=${encodeURIComponent(query)}`, {
      headers: { Accept: "application/json" },
    })
    if (!response.ok) {
      throw new Error(`Plan request failed with status ${response.status}`)
    }
    host.innerHTML = renderExplainPlan(await response.json())
  } catch (error) {
    const message = error instanceof Error ? error.message : "Plan request failed."
    host.innerHTML = `<p class="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger" role="alert">${escapeHtml(
      message,
    )}</p>`
  }
}

export const showTelemetryPopover = (detail) => {
  const root = document.querySelector("[data-ui-popover-root='chat']")
  if (!root) {
    return
  }
  const sqlPhases = Array.isArray(detail.sqlPhases) ? detail.sqlPhases : []
  const planQuery = typeof detail.planQuery === "string" && detail.planQuery.trim() ? detail.planQuery.trim() : null
  const sqlMarkup = sqlPhases.length
    ? sqlPhases.map(renderSqlPhase).join("")
    : '<p class="mt-2 text-sm text-muted">No SQL was executed for this phase.</p>'
  root.hidden = false
  root.removeAttribute("aria-hidden")
  root.setAttribute("role", "dialog")
  root.className = "popover-surface fixed bottom-4 right-4 z-50 max-h-[70vh] w-[min(34rem,calc(100vw-2rem))] overflow-auto p-4"
  root.innerHTML = `<header class="flex items-start justify-between gap-3">
    <div>
      <h2 class="text-base font-semibold text-strong">${escapeHtml(detail.title ?? "Telemetry")}</h2>
      <p class="mt-1 text-sm text-muted">${escapeHtml(detail.summary ?? "")}</p>
    </div>
    <button type="button" class="icon-button" data-telemetry-close aria-label="Close telemetry detail">X</button>
  </header>
  ${
    planQuery
      ? `<section class="mt-3 border-t border-border pt-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h3 class="text-sm font-semibold text-strong">Oracle vector search</h3>
            <span class="font-mono text-xs text-muted">${escapeHtml(planQuery)}</span>
          </div>
          <div data-explain-plan-host class="mt-3">
            <p class="border-l-2 border-accent/40 py-1 pl-3 text-xs text-muted">Loading EXPLAIN PLAN...</p>
          </div>
          <div class="mt-3">
            <h3 class="text-xs font-semibold uppercase text-muted">SQL</h3>
            ${sqlMarkup}
          </div>
        </section>`
      : `<div class="mt-3">
          <h3 class="text-xs font-semibold uppercase text-muted">SQL</h3>
          ${sqlMarkup}
        </div>`
  }`
  const closeButton = root.querySelector("[data-telemetry-close]")
  if (closeButton instanceof HTMLElement) {
    closeButton.focus()
  }
  if (planQuery) {
    void loadExplainPlan(planQuery)
  }
}

export const hideTelemetryPopover = () => {
  const root = document.querySelector("[data-ui-popover-root='chat']")
  if (!root) {
    return
  }
  root.hidden = true
  root.setAttribute("aria-hidden", "true")
  root.removeAttribute("role")
  root.className = "popover-surface sr-only"
  root.innerHTML = ""
}

export const renderMessageTelemetry = (payload) => {
  const target = document.getElementById("pending-reply-meta")
  if (!target) {
    return
  }

  const metrics = payload.search_metrics ?? {}
  const vectorQuery = metrics.vector_query ?? metrics.query
  const chips = [
    payload.intent_detected
      ? telemetryChip(
          "I",
          "Intent",
          payload.intent_detected,
          "neutral",
          telemetryDetail(
            "Intent classification",
            `The request was classified as ${payload.intent_detected}.`,
            [],
          ),
        )
      : null,
    vectorQuery
      ? telemetryChip(
          "Q",
          "Vector query",
          `"${vectorQuery}"`,
          "neutral",
          telemetryDetail(
            "Oracle vector search",
            `The product RAG lookup used "${vectorQuery}".`,
            phasesFor(payload, "vector-search-products"),
            { planQuery: vectorQuery },
          ),
        )
      : null,
    formatMetricMs(metrics.total_ms)
      ? telemetryChip(
          "T",
          "Total response",
          formatMetricMs(metrics.total_ms),
          "neutral",
          telemetryDetail("Total response runtime", `The full turn completed in ${formatMetricMs(metrics.total_ms)}.`, payloadSqlPhases(payload)),
        )
      : null,
    formatMetricMs(metrics.embedding_ms)
      ? telemetryChip(
          "E",
          "Embedding phase",
          formatMetricMs(metrics.embedding_ms),
          "neutral",
          telemetryDetail(
            "Embedding phase",
            `Embedding work completed in ${formatMetricMs(metrics.embedding_ms)}.`,
            phasesFor(payload, "get-cached-embedding"),
          ),
        )
      : null,
    formatMetricMs(metrics.oracle_ms)
      ? telemetryChip(
          "O",
          "Oracle vector phase",
          formatMetricMs(metrics.oracle_ms),
          "neutral",
          telemetryDetail(
            "Oracle vector phase",
            `Oracle vector search completed in ${formatMetricMs(metrics.oracle_ms)}.`,
            phasesFor(payload, "vector-search-products"),
            vectorQuery ? { planQuery: vectorQuery } : {},
          ),
        )
      : null,
    payload.embedding_cache_hit
      ? telemetryChip(
          "E",
          "Embedding cache",
          "hit",
          "hit",
          telemetryDetail("Embedding cache", "The query embedding was served from the embedding cache.", phasesFor(payload, "get-cached-embedding")),
        )
      : null,
    payload.from_cache
      ? telemetryChip(
          "R",
          "Response cache",
          "hit",
          "hit",
          telemetryDetail("Response cache", "The final answer was served from the response cache.", phasesFor(payload, "get-cached-response")),
        )
      : null,
  ].filter(Boolean)

  target.hidden = chips.length === 0
  target.innerHTML = chips.join("")
}

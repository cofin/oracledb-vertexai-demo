// Copyright 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import htmx from "htmx.org"
import ApexCharts from "apexcharts"
import { registerHtmxExtension } from "litestar-vite-plugin/helpers"

window.htmx = htmx
window.ApexCharts = ApexCharts
registerHtmxExtension()

const processHtmxDom = () => {
  if (document.body) {
    htmx.process(document.body)
  }
}

const onReady = (callback) => {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", callback, { once: true })
  } else {
    callback()
  }
}

const escapeHtml = (value) => {
  const div = document.createElement("div")
  div.textContent = value
  return div.innerHTML
}

const encodeDetail = (detail) => escapeHtml(JSON.stringify(detail))

const GEOLOCATION_OPTIONS = {
  enableHighAccuracy: false,
  timeout: 8000,
  maximumAge: 300000,
}

const chatLocationState = {
  coordinates: null,
}

const scrollMessages = () => {
  const messages = document.getElementById("messages")
  if (messages) {
    messages.scrollTop = messages.scrollHeight
  }
}

const removePendingReply = () => {
  document.getElementById("pending-reply")?.remove()
}

const welcomeMessageHtml = () => `<div class="message-row message-row-ai">
  <div class="chat-avatar chat-avatar-ai" data-chat-avatar="ai" aria-hidden="true">B</div>
  <article class="message message-ai px-4 py-3 shadow-sm">
    <header class="flex items-center justify-between text-xs">
      <span class="font-medium text-muted">Barista</span>
      <span class="telemetry-chip border-sage/25 bg-sage/10 text-sage">READY</span>
    </header>
    <p class="mt-2 whitespace-pre-wrap text-base text-strong">
      Tell me what sounds good and I'll check the Cymbal Coffee menu.
    </p>
  </article>
</div>`

const resetChatMessages = () => {
  const messages = document.getElementById("messages")
  if (messages) {
    messages.innerHTML = welcomeMessageHtml()
  }
  const metrics = document.getElementById("metrics-badges")
  if (metrics) {
    metrics.innerHTML = ""
  }
  hideTelemetryPopover()
  clearChatError()
  scrollMessages()
}

const setFormBusy = (form, isBusy) => {
  for (const control of form.querySelectorAll("button, input[name='message']")) {
    control.disabled = isBusy
  }
}

const renderMetrics = (payload) => {
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

const telemetryDetail = (title, summary, sqlPhases = []) => ({
  title,
  summary,
  sqlPhases,
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
        `<div class="help-tooltip-metric"><span class="help-tooltip-metric-label">${escapeHtml(key)}</span><span class="help-tooltip-metric-value">${escapeHtml(
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

const showTelemetryPopover = (detail) => {
  const root = document.querySelector("[data-ui-popover-root='chat']")
  if (!root) {
    return
  }
  const sqlPhases = Array.isArray(detail.sqlPhases) ? detail.sqlPhases : []
  root.hidden = false
  root.className = "popover-surface fixed bottom-4 right-4 z-50 max-h-[70vh] w-[min(34rem,calc(100vw-2rem))] overflow-auto p-4"
  root.innerHTML = `<header class="flex items-start justify-between gap-3">
    <div>
      <h2 class="text-base font-semibold text-strong">${escapeHtml(detail.title ?? "Telemetry")}</h2>
      <p class="mt-1 text-sm text-muted">${escapeHtml(detail.summary ?? "")}</p>
    </div>
    <button type="button" class="icon-button" data-telemetry-close aria-label="Close telemetry detail">X</button>
  </header>
  <div class="mt-3">
    <h3 class="text-xs font-semibold uppercase text-muted">SQL</h3>
    ${sqlPhases.length ? sqlPhases.map(renderSqlPhase).join("") : '<p class="mt-2 text-sm text-muted">No SQL was executed for this phase.</p>'}
  </div>`
}

const hideTelemetryPopover = () => {
  const root = document.querySelector("[data-ui-popover-root='chat']")
  if (!root) {
    return
  }
  root.hidden = true
  root.className = "popover-surface sr-only"
  root.innerHTML = ""
}

const renderMessageTelemetry = (payload) => {
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
            "Product lookup query",
            `The product RAG lookup used "${vectorQuery}".`,
            phasesFor(payload, "vector-search-products"),
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

const showChatError = (message) => {
  const target = document.getElementById("chat-error")
  if (target) {
    target.innerHTML = `<p class="py-2 text-sm text-danger">${escapeHtml(message)}</p>`
  }
}

const clearChatError = () => {
  const target = document.getElementById("chat-error")
  if (target) {
    target.innerHTML = ""
  }
}

const locationField = (form, selector) => {
  const field = form.querySelector(selector)
  return field instanceof HTMLInputElement ? field : null
}

const setLocationFieldValue = (form, selector, value) => {
  const field = locationField(form, selector)
  if (field) {
    field.value = value
  }
}

const setLocationStatus = (form, message, variant = "muted") => {
  const target = form.querySelector("[data-location-status]")
  if (!(target instanceof HTMLElement)) {
    return
  }
  target.textContent = message
  target.classList.toggle("text-success", variant === "success")
  target.classList.toggle("text-danger", variant === "danger")
  target.classList.toggle("text-muted", variant === "muted")
}

const clearLocationCoordinates = (form) => {
  chatLocationState.coordinates = null
  setLocationFieldValue(form, "[data-location-consent]", "false")
  setLocationFieldValue(form, "[data-location-latitude]", "")
  setLocationFieldValue(form, "[data-location-longitude]", "")
  setLocationFieldValue(form, "[data-location-accuracy]", "")
}

const setLocationCoordinates = (form, coordinates) => {
  chatLocationState.coordinates = coordinates
  setLocationFieldValue(form, "[data-location-consent]", "true")
  setLocationFieldValue(form, "[data-location-latitude]", String(coordinates.latitude))
  setLocationFieldValue(form, "[data-location-longitude]", String(coordinates.longitude))
  setLocationFieldValue(form, "[data-location-accuracy]", String(Math.max(coordinates.accuracy ?? 0, 0)))
}

const locationErrorMessage = (error) => {
  if (!error || typeof error.code !== "number") {
    return "Location unavailable"
  }
  if (error.code === 1) {
    return "Location denied"
  }
  if (error.code === 3) {
    return "Location timed out"
  }
  return "Location unavailable"
}

const requestBrowserLocation = (form, button) => {
  if (!("geolocation" in navigator)) {
    clearLocationCoordinates(form)
    setLocationStatus(form, "Location unsupported", "danger")
    return
  }

  button.disabled = true
  setLocationStatus(form, "Locating...", "muted")
  navigator.geolocation.getCurrentPosition(
    (position) => {
      setLocationCoordinates(form, {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      })
      setLocationStatus(form, "Location ready", "success")
      button.disabled = false
    },
    (error) => {
      clearLocationCoordinates(form)
      setLocationStatus(form, locationErrorMessage(error), "danger")
      button.disabled = false
    },
    GEOLOCATION_OPTIONS,
  )
}

const setPersona = (persona) => {
  const input = document.querySelector("[data-persona-input]")
  const buttons = document.querySelectorAll("[data-persona-option]")
  if (input instanceof HTMLInputElement) {
    input.value = persona
  }
  for (const button of buttons) {
    const selected = button.getAttribute("data-persona-option") === persona
    button.setAttribute("aria-pressed", String(selected))
    button.classList.toggle("border-accent", selected)
    button.classList.toggle("bg-accent-soft", selected)
    button.classList.toggle("text-accent-strong", selected)
    button.classList.toggle("border-border", !selected)
    button.classList.toggle("bg-surface", !selected)
    button.classList.toggle("text-muted", !selected)
    button.classList.toggle("hover:text-strong", !selected)
  }
}

const initPersonaPicker = () => {
  const picker = document.querySelector("[data-persona-picker]")
  if (!picker) {
    return
  }
  picker.addEventListener("click", (event) => {
    const button = event.target instanceof Element ? event.target.closest("[data-persona-option]") : null
    if (button instanceof HTMLButtonElement) {
      setPersona(button.dataset.personaOption ?? "enthusiast")
    }
  })
  const selected = picker.querySelector('[data-persona-option][aria-pressed="true"]')
  setPersona(selected instanceof HTMLElement ? (selected.dataset.personaOption ?? "enthusiast") : "enthusiast")
}

const renderEmptyChart = (host, message) => {
  host.replaceChildren()
  const empty = document.createElement("div")
  empty.className = "flex h-full min-h-64 items-center justify-center text-sm font-medium text-muted"
  empty.textContent = message
  host.appendChild(empty)
}

const initDashboardCharts = async () => {
  const root = document.querySelector("[data-dashboard-charts]")
  if (!(root instanceof HTMLElement) || root.dataset.chartsReady === "true") {
    return
  }
  root.dataset.chartsReady = "true"
  const responseHost = root.querySelector('[data-chart-host="response-trends"]')
  const scatterHost = root.querySelector('[data-chart-host="vector-performance"]')
  const breakdownHost = root.querySelector('[data-chart-host="system-breakdown"]')
  if (!(responseHost instanceof HTMLElement) || !(scatterHost instanceof HTMLElement) || !(breakdownHost instanceof HTMLElement)) {
    return
  }

  const data = await fetch("/api/metrics/charts").then((response) => response.json())
  const timeSeries = data.timeSeries ?? { labels: [], series: {} }
  const series = timeSeries.series ?? {}
  const scatter = Array.isArray(data.scatter) ? data.scatter : []
  const breakdown = data.breakdown ?? { labels: [], values: [] }
  const hasTrendData = Array.isArray(timeSeries.labels) && timeSeries.labels.length > 0
  const trendLabels = hasTrendData ? timeSeries.labels : ["No data"]
  const totalSeries = hasTrendData ? (series.totalMs ?? []) : [0]
  const oracleSeries = hasTrendData ? (series.oracleMs ?? []) : [0]
  const embeddingSeries = hasTrendData ? (series.embeddingMs ?? []) : [0]
  const breakdownValues = Array.isArray(breakdown.values) ? breakdown.values.map(Number) : []
  const hasBreakdownData = breakdownValues.some((value) => value > 0)
  const breakdownData = hasBreakdownData
    ? breakdown.labels.map((label, index) => ({ x: label, y: breakdownValues[index] ?? 0 }))
    : []
  const charts = []

  if (hasTrendData) {
    charts.push(
      new ApexCharts(responseHost, {
        chart: { type: "line", height: 286, foreColor: "#77675f", toolbar: { show: false } },
        stroke: { curve: "smooth", width: [3, 2, 2] },
        grid: { borderColor: "rgba(143, 95, 67, 0.16)" },
        markers: { size: 3 },
        xaxis: { categories: trendLabels },
        yaxis: { title: { text: "Milliseconds" } },
        colors: ["#8f5f43", "#587487", "#6f8064"],
        series: [
          { name: "Total response", data: totalSeries },
          { name: "Oracle vector", data: oracleSeries },
          { name: "Embedding", data: embeddingSeries },
        ],
      }),
    )
  } else {
    renderEmptyChart(responseHost, "No response metrics yet")
  }

  if (scatter.length > 0) {
    charts.push(
      new ApexCharts(scatterHost, {
        chart: { type: "scatter", height: 286, foreColor: "#77675f", toolbar: { show: false } },
        grid: { borderColor: "rgba(143, 95, 67, 0.16)" },
        colors: ["#8f5f43"],
        xaxis: {
          min: 0,
          max: 1,
          tickAmount: 5,
          title: { text: "Similarity score" },
        },
        yaxis: { title: { text: "Total ms" } },
        series: [
          {
            name: "Query performance",
            data: scatter.map((point) => ({ x: point.similarityScore, y: point.totalMs })),
          },
        ],
      }),
    )
  } else {
    renderEmptyChart(scatterHost, "No vector metrics yet")
  }

  if (hasBreakdownData) {
    charts.push(
      new ApexCharts(breakdownHost, {
        chart: { type: "bar", height: 286, foreColor: "#77675f", toolbar: { show: false } },
        colors: ["#8f5f43"],
        grid: { borderColor: "rgba(143, 95, 67, 0.16)" },
        legend: { show: false },
        plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: "58%" } },
        xaxis: { title: { text: "Average ms" } },
        series: [{ name: "Average ms", data: breakdownData }],
      }),
    )
  } else {
    renderEmptyChart(breakdownHost, "No component metrics yet")
  }

  for (const chart of charts) {
    chart.render()
  }
}

const rowValue = (row, keys, fallback = "") => {
  for (const key of keys) {
    const value = row?.[key]
    if (value !== undefined && value !== null && value !== "") {
      return value
    }
  }
  return fallback
}

const formatLocality = (row) =>
  [
    rowValue(row, ["store_city", "storeCity", "city"]),
    [rowValue(row, ["store_state", "storeState", "state"]), rowValue(row, ["store_zip", "storeZip", "zip"])].filter(Boolean).join(" "),
  ]
    .filter(Boolean)
    .join(", ")

const formatHoursSummary = (hours) => {
  if (typeof hours === "string") {
    return hours
  }
  if (!hours || typeof hours !== "object") {
    return ""
  }
  const monday = hours.monday ?? hours.Monday
  if (monday) {
    return `Mon ${monday}`
  }
  const first = Object.entries(hours).find(([, value]) => value)
  return first ? `${first[0].slice(0, 3)} ${first[1]}` : ""
}

const formatDistance = (value) => {
  const distance = Number(value)
  if (!Number.isFinite(distance)) {
    return ""
  }
  return `${distance < 10 ? distance.toFixed(1) : Math.round(distance)} mi`
}

const formatStockStatus = (value) =>
  String(value || "")
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase())

const safeMapsUrl = (url) => {
  try {
    const parsed = new URL(url)
    if (parsed.protocol === "https:" && parsed.hostname === "www.google.com" && parsed.pathname.startsWith("/maps/")) {
      return parsed.href
    }
  } catch {
    return null
  }
  return null
}

const mapActionForRow = (row, actions) => {
  const name = String(rowValue(row, ["store_name", "storeName", "name"], ""))
  const action = actions.find((candidate) => candidate?.label === name) ?? actions[0]
  const url = action ? safeMapsUrl(action.url) : null
  return url ? { ...action, url } : null
}

const renderStoreCard = (row, action) => {
  const name = rowValue(row, ["store_name", "storeName", "name"], "Cymbal Coffee")
  const address = rowValue(row, ["store_address", "storeAddress", "address"])
  const locality = formatLocality(row)
  const phone = rowValue(row, ["phone", "store_phone", "storePhone"])
  const hours = formatHoursSummary(rowValue(row, ["hours"], null))
  const distance = formatDistance(rowValue(row, ["distance_miles", "distanceMiles"], null))
  const productName = rowValue(row, ["product_name", "productName"])
  const quantity = rowValue(row, ["quantity_available", "quantityAvailable"], null)
  const stockStatus = rowValue(row, ["stock_status", "stockStatus"])
  const pickupAvailable = rowValue(row, ["pickup_available", "pickupAvailable"], null)
  const stockClass =
    stockStatus === "IN_STOCK"
      ? "border-success/25 bg-success/10 text-success"
      : stockStatus === "LOW_STOCK"
        ? "border-accent/25 bg-accent-soft text-accent-strong"
        : "border-danger/25 bg-danger/10 text-danger"

  return `<article class="mt-3 rounded-lg border border-border bg-surface-strong/60 p-3">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <h3 class="text-sm font-semibold text-strong">${escapeHtml(String(name))}</h3>
        <p class="mt-1 text-xs text-muted">${escapeHtml([address, locality].filter(Boolean).join(", "))}</p>
      </div>
      ${distance ? `<span class="telemetry-chip border-sage/25 bg-sage/10 text-sage">${escapeHtml(distance)}</span>` : ""}
    </div>
    <div class="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-2">
      ${phone ? `<span>${escapeHtml(String(phone))}</span>` : ""}
      ${hours ? `<span>${escapeHtml(hours)}</span>` : ""}
      ${productName ? `<span class="font-medium text-strong">${escapeHtml(String(productName))}</span>` : ""}
      ${quantity !== null ? `<span>${escapeHtml(String(quantity))} available</span>` : ""}
    </div>
    <div class="mt-3 flex flex-wrap items-center gap-2">
      ${stockStatus ? `<span class="telemetry-chip ${stockClass}">${escapeHtml(formatStockStatus(stockStatus))}</span>` : ""}
      ${
        pickupAvailable !== null
          ? `<span class="telemetry-chip border-border bg-surface text-muted">${pickupAvailable ? "Pickup available" : "Pickup unavailable"}</span>`
          : ""
      }
      ${
        action
          ? `<a href="${escapeHtml(action.url)}" target="_blank" rel="noopener noreferrer" class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-accent-strong transition-colors hover:border-accent/40 hover:bg-accent-soft">Open in Google Maps</a>`
          : ""
      }
    </div>
  </article>`
}

const renderStructuredResults = (payload) => {
  const target = document.getElementById("pending-reply-results")
  if (!target) {
    return
  }
  const inventory = Array.isArray(payload.inventory_results) ? payload.inventory_results : []
  const stores = Array.isArray(payload.store_results) ? payload.store_results : []
  const rows = inventory.length ? inventory : stores
  const actions = Array.isArray(payload.map_actions) ? payload.map_actions : []
  if (rows.length === 0) {
    target.hidden = true
    target.innerHTML = ""
    return
  }
  target.hidden = false
  target.innerHTML = rows
    .slice(0, 3)
    .map((row) => renderStoreCard(row, mapActionForRow(row, actions)))
    .join("")
}

const appendUserAndPendingMessages = (message) => {
  const messages = document.getElementById("messages")
  if (!messages) {
    return
  }

  removePendingReply()
  messages.insertAdjacentHTML(
    "beforeend",
    `<div class="message-row message-row-human">
      <div class="chat-avatar chat-avatar-human" data-chat-avatar="human" aria-hidden="true">Y</div>
      <article class="message message-human px-4 py-3 shadow-sm">
        <header class="flex items-center justify-between gap-3 text-xs">
          <span class="font-medium text-muted">You</span>
        </header>
        <p class="mt-2 whitespace-pre-wrap text-base text-strong">${escapeHtml(message)}</p>
      </article>
    </div>
    <div id="pending-reply" class="message-row message-row-ai">
      <div class="chat-avatar chat-avatar-ai" data-chat-avatar="ai" aria-hidden="true">B</div>
      <article class="message message-ai px-4 py-3 shadow-sm">
        <header class="flex items-center justify-between gap-3 text-xs">
          <span class="font-medium text-muted">Barista</span>
        </header>
        <p id="pending-reply-text" class="mt-2 whitespace-pre-wrap text-base text-strong"></p>
        <div id="pending-reply-meta" class="mt-3 flex flex-wrap items-center gap-1.5 text-[11px]" hidden></div>
        <div id="pending-reply-results" class="mt-3" hidden></div>
        <div class="mt-3 flex items-center gap-1.5">
          <span class="typing-dot h-2 w-2 rounded-full bg-accent"></span>
          <span class="typing-dot h-2 w-2 rounded-full bg-accent"></span>
          <span class="typing-dot h-2 w-2 rounded-full bg-accent"></span>
        </div>
      </article>
    </div>`,
  )
  scrollMessages()
}

const appendPendingText = (text) => {
  const target = document.getElementById("pending-reply-text")
  const pending = document.getElementById("pending-reply")
  if (!target || !pending) {
    return
  }
  pending.querySelector(".typing-dot")?.parentElement?.remove()
  target.textContent += text
  scrollMessages()
}

const setPendingText = (text) => {
  const target = document.getElementById("pending-reply-text")
  const pending = document.getElementById("pending-reply")
  if (!target || !pending) {
    return
  }
  pending.querySelector(".typing-dot")?.parentElement?.remove()
  target.textContent = text
  scrollMessages()
}

const finalizePendingReply = () => {
  const pending = document.getElementById("pending-reply")
  const target = document.getElementById("pending-reply-text")
  pending?.querySelector(".typing-dot")?.parentElement?.remove()
  pending?.querySelector("#pending-reply-meta")?.removeAttribute("id")
  pending?.querySelector("#pending-reply-results")?.removeAttribute("id")
  pending?.removeAttribute("id")
  target?.removeAttribute("id")
}

const parseSseBlock = (block) => {
  let eventName = "message"
  const dataLines = []
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim()
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart())
    }
  }
  if (dataLines.length === 0) {
    return null
  }
  return { eventName, data: dataLines.join("\n") }
}

const handleChatStreamEvent = ({ eventName, data }) => {
  const payload = JSON.parse(data)
  if (eventName === "delta") {
    appendPendingText(payload.text ?? "")
    return
  }
  if (eventName === "final") {
    setPendingText(payload.answer ?? "")
    renderMessageTelemetry(payload)
    renderStructuredResults(payload)
    renderMetrics(payload)
    finalizePendingReply()
    return
  }
  if (eventName === "error") {
    const message = payload.message ?? "Chat failed. Please try again."
    setPendingText(message)
    showChatError(message)
    finalizePendingReply()
  }
}

const readEventStream = async (response) => {
  if (!response.body) {
    throw new Error("Streaming response body is unavailable")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n")
    let boundary = buffer.indexOf("\n\n")
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const event = parseSseBlock(block)
      if (event) {
        handleChatStreamEvent(event)
      }
      boundary = buffer.indexOf("\n\n")
    }
  }
}

document.body.addEventListener("submit", async (event) => {
  const form = event.target
  if (!(form instanceof HTMLFormElement) || form.dataset.chatForm !== "true") {
    return
  }
  event.preventDefault()

  const input = form.elements.namedItem("message")
  if (!(input instanceof HTMLInputElement)) {
    return
  }

  const message = input.value.trim()
  if (!message) {
    return
  }

  const formData = new FormData(form)
  formData.set("message", message)

  clearChatError()
  appendUserAndPendingMessages(message)
  setFormBusy(form, true)

  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: formData,
      headers: { Accept: "text/event-stream" },
    })
    if (!response.ok) {
      throw new Error(`Chat failed with status ${response.status}`)
    }
    await readEventStream(response)
    input.value = ""
  } catch (error) {
    const messageText = error instanceof Error ? error.message : "Chat failed. Please try again."
    setPendingText(messageText)
    showChatError(messageText)
    finalizePendingReply()
  } finally {
    setFormBusy(form, false)
    scrollMessages()
  }
})

document.body.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) {
    return
  }
  const useLocation = event.target.closest("[data-use-location]")
  if (useLocation instanceof HTMLButtonElement && useLocation.form instanceof HTMLFormElement) {
    requestBrowserLocation(useLocation.form, useLocation)
    return
  }
  const close = event.target.closest("[data-telemetry-close]")
  if (close) {
    hideTelemetryPopover()
    return
  }
  const clearChat = event.target.closest("[data-clear-chat]")
  if (clearChat) {
    fetch("/api/chat/session/clear", { method: "POST", headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Clear chat failed with status ${response.status}`)
        }
        resetChatMessages()
      })
      .catch((error) => {
        const messageText = error instanceof Error ? error.message : "Clear chat failed. Please try again."
        showChatError(messageText)
      })
    return
  }
  const trigger = event.target.closest("[data-telemetry-detail]")
  if (!(trigger instanceof HTMLElement)) {
    return
  }
  const raw = trigger.dataset.telemetryDetail
  if (!raw) {
    return
  }
  showTelemetryPopover(JSON.parse(raw))
})

onReady(() => {
  processHtmxDom()
  initPersonaPicker()
  void initDashboardCharts()
  scrollMessages()
})

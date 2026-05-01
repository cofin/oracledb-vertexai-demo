// Copyright 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import htmx from "htmx.org"
import Alpine from "alpinejs"
import ApexCharts from "apexcharts"
import { registerHtmxExtension } from "litestar-vite-plugin/helpers"
import "./styles.css"

window.htmx = htmx
window.Alpine = Alpine
window.ApexCharts = ApexCharts
Alpine.start()
registerHtmxExtension()

const escapeHtml = (value) => {
  const div = document.createElement("div")
  div.textContent = value
  return div.innerHTML
}

const encodeDetail = (detail) => escapeHtml(JSON.stringify(detail))

const scrollMessages = () => {
  const messages = document.getElementById("messages")
  if (messages) {
    messages.scrollTop = messages.scrollHeight
  }
}

const removePendingReply = () => {
  document.getElementById("pending-reply")?.remove()
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

const appendUserAndPendingMessages = (message) => {
  const messages = document.getElementById("messages")
  if (!messages) {
    return
  }

  removePendingReply()
  messages.insertAdjacentHTML(
    "beforeend",
    `<article class="message message-human rounded-lg border px-4 py-3 shadow-sm">
      <header class="flex items-center justify-between gap-3 text-xs">
        <span class="font-medium text-muted">You</span>
      </header>
      <p class="mt-2 whitespace-pre-wrap text-base text-strong">${escapeHtml(message)}</p>
    </article>
    <article id="pending-reply" class="message message-ai rounded-lg border border-border px-4 py-3 shadow-sm">
      <header class="flex items-center justify-between gap-3 text-xs">
        <span class="font-medium text-muted">Barista</span>
      </header>
      <p id="pending-reply-text" class="mt-2 whitespace-pre-wrap text-base text-strong"></p>
      <div id="pending-reply-meta" class="mt-3 flex flex-wrap items-center gap-1.5 text-[11px]" hidden></div>
      <div class="mt-3 flex items-center gap-1.5">
        <span class="typing-dot h-2 w-2 rounded-full bg-accent"></span>
        <span class="typing-dot h-2 w-2 rounded-full bg-accent"></span>
        <span class="typing-dot h-2 w-2 rounded-full bg-accent"></span>
      </div>
    </article>`,
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
  const close = event.target.closest("[data-telemetry-close]")
  if (close) {
    hideTelemetryPopover()
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

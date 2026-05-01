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

const telemetryChip = (icon, label, value, variant = "neutral") => {
  const variantClass =
    variant === "hit"
      ? "border-success/25 bg-success/10 text-success"
      : "border-border bg-surface-strong/55 text-muted"
  return `<span class="telemetry-chip ${variantClass}" data-telemetry-chip title="${escapeHtml(
    `${label}: ${value}`,
  )}">
    <span class="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-surface text-[10px] font-semibold text-accent-strong" aria-hidden="true">${icon}</span>
    <span class="truncate">${escapeHtml(String(value))}</span>
  </span>`
}

const renderMessageTelemetry = (payload) => {
  const target = document.getElementById("pending-reply-meta")
  if (!target) {
    return
  }

  const metrics = payload.search_metrics ?? {}
  const vectorQuery = metrics.vector_query ?? metrics.query
  const chips = [
    payload.intent_detected ? telemetryChip("I", "Intent", payload.intent_detected) : null,
    vectorQuery ? telemetryChip("Q", "Vector query", `"${vectorQuery}"`) : null,
    formatMetricMs(metrics.total_ms) ? telemetryChip("T", "Total response", formatMetricMs(metrics.total_ms)) : null,
    formatMetricMs(metrics.embedding_ms)
      ? telemetryChip("E", "Embedding phase", formatMetricMs(metrics.embedding_ms))
      : null,
    formatMetricMs(metrics.oracle_ms) ? telemetryChip("O", "Oracle vector phase", formatMetricMs(metrics.oracle_ms)) : null,
    payload.embedding_cache_hit ? telemetryChip("E", "Embedding cache", "hit", "hit") : null,
    payload.from_cache ? telemetryChip("R", "Response cache", "hit", "hit") : null,
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

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
  const badges = [
    ["Intent", payload.intent_detected],
    ["Total", Number.isFinite(metrics.total_ms) ? `${metrics.total_ms} ms` : null],
    ["Oracle", Number.isFinite(metrics.oracle_ms) ? `${metrics.oracle_ms} ms` : null],
    ["Embedding", Number.isFinite(metrics.embedding_ms) ? `${metrics.embedding_ms} ms` : null],
    ["Source", payload.from_cache ? "Cache" : "Live"],
  ].filter(([, value]) => value)

  target.innerHTML = badges
    .map(
      ([label, value]) =>
        `<span class="rounded-full border border-border bg-accent-soft px-2.5 py-1 text-accent-strong">${label}: ${escapeHtml(String(value))}</span>`,
    )
    .join("")
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
    const currentText = document.getElementById("pending-reply-text")?.textContent ?? ""
    if (!currentText.trim()) {
      setPendingText(payload.answer ?? "")
    }
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

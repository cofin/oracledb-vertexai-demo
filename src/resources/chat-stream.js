// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import { escapeHtml, scrollMessages } from "./util.js"
import { hideTelemetryPopover, renderMessageTelemetry, renderMetrics } from "./telemetry.js"
import { triggerBlackBeltRain } from "./easter-egg.js"

const removePendingReply = () => {
  document.getElementById("pending-reply")?.remove()
}

const resetChatMessages = () => {
  const messages = document.getElementById("messages")
  const template = document.querySelector("template[data-chat-welcome]")
  if (messages && template instanceof HTMLTemplateElement) {
    messages.innerHTML = template.innerHTML
  } else if (messages) {
    messages.innerHTML = ""
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

const validateMapAction = (action) => {
  const url = action ? safeMapsUrl(action.url) : null
  return url ? { ...action, url } : null
}

const mapActionsForRow = (rowIndex, actions) => {
  const search = validateMapAction(actions[rowIndex * 2])
  const directions = validateMapAction(actions[rowIndex * 2 + 1])
  return { search, directions }
}

const renderStoreCard = (row, mapActions) => {
  const { search, directions } = mapActions || {}
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
        search
          ? `<a href="${escapeHtml(search.url)}" target="_blank" rel="noopener noreferrer" class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-accent-strong transition-colors hover:border-accent/40 hover:bg-accent-soft">Open in Google Maps</a>`
          : ""
      }
      ${
        directions
          ? `<a href="${escapeHtml(directions.url)}" target="_blank" rel="noopener noreferrer" class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-accent-strong transition-colors hover:border-accent/40 hover:bg-accent-soft">Get directions</a>`
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
    .map((row, index) => renderStoreCard(row, mapActionsForRow(index, actions)))
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

const announceToScreenReader = (text) => {
  const announcer = document.getElementById("chat-live-announcer")
  if (announcer) {
    announcer.textContent = text
  }
}

const handleChatStreamEvent = ({ eventName, data }) => {
  const payload = JSON.parse(data)
  if (eventName === "delta") {
    appendPendingText(payload.text ?? "")
    const target = document.getElementById("pending-reply-text")
    if (target && target.textContent.includes("BLACK_BELT_MODE_ENGAGED")) {
      triggerBlackBeltRain()
    }
    return
  }
  if (eventName === "final") {
    const answer = payload.answer ?? ""
    setPendingText(answer)
    renderMessageTelemetry(payload)
    renderStructuredResults(payload)
    renderMetrics(payload)
    finalizePendingReply()
    announceToScreenReader(answer)
    return
  }
  if (eventName === "error") {
    const message = payload.message ?? "Chat failed. Please try again."
    setPendingText(message)
    showChatError(message)
    finalizePendingReply()
    announceToScreenReader(message)
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

export const handleChatSubmit = async (form) => {
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

  if (/make\s*it\s*rain|cyber\s*barista|matrix/i.test(message)) {
    triggerBlackBeltRain()
  }

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
}

export const handleClearChat = () => {
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
}

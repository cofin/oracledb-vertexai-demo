// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import htmx from "htmx.org"
import { registerHtmxExtension } from "litestar-vite-plugin/helpers"
import { initVectorCalculator } from "./vector-calculator.js"
import { onReady, processHtmxDom, scrollMessages } from "./util.js"
import { initDashboardCharts } from "./charts.js"
import { hideTelemetryPopover, showTelemetryPopover } from "./telemetry.js"
import { requestBrowserLocation } from "./geolocation.js"
import { handleChatSubmit, handleClearChat } from "./chat-stream.js"

window.htmx = htmx
registerHtmxExtension()

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

document.body.addEventListener("submit", async (event) => {
  const form = event.target
  if (!(form instanceof HTMLFormElement) || form.dataset.chatForm !== "true") {
    return
  }
  event.preventDefault()
  await handleChatSubmit(form)
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
    handleClearChat()
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
  void initVectorCalculator()
  scrollMessages()
})

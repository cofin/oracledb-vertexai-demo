// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import htmx from "htmx.org"

export const processHtmxDom = () => {
  if (document.body) {
    htmx.process(document.body)
  }
}

export const onReady = (callback) => {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", callback, { once: true })
  } else {
    callback()
  }
}

export const escapeHtml = (value) => {
  const div = document.createElement("div")
  div.textContent = value
  return div.innerHTML
}

export const encodeDetail = (detail) => escapeHtml(JSON.stringify(detail))

export const scrollMessages = () => {
  const messages = document.getElementById("messages")
  if (messages) {
    messages.scrollTop = messages.scrollHeight
  }
}

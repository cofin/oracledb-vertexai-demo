// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

const GEOLOCATION_OPTIONS = {
  enableHighAccuracy: false,
  timeout: 8000,
  maximumAge: 300000,
}

const chatLocationState = {
  coordinates: null,
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

export const requestBrowserLocation = (form, button) => {
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

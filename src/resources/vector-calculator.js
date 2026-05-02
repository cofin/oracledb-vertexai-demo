// Copyright 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

const KIB = 1024
const MIB = KIB ** 2
const GIB = KIB ** 3
const TIB = KIB ** 4

const ROW_MIN = 1_000
const ROW_MAX = 100_000_000
const DIMENSION_MIN = 1
const DIMENSION_MAX = 4_096
const HNSW_M_MIN = 8
const HNSW_M_MAX = 128

const DEFAULTS = {
  rowCount: 1_000_000,
  dimensions: 3_072,
  format: "FLOAT32",
  indexType: "HNSW",
  hnswM: 16,
}

const FORMAT_BYTES = {
  FLOAT64: 8,
  FLOAT32: 4,
  INT8: 1,
}

const MEDIA_REFERENCES = [
  { label: "floppy disk", plural: "floppy disks", bytes: 1.44 * MIB },
  { label: "CD-ROM", plural: "CD-ROMs", bytes: 700 * MIB },
  { label: "DVD", plural: "DVDs", bytes: 4.7 * GIB },
  { label: "Blu-ray disc", plural: "Blu-ray discs", bytes: 25 * GIB },
  { label: "1 TB NVMe drive", plural: "1 TB NVMe drives", bytes: TIB },
]

const clamp = (value, min, max) => Math.min(Math.max(value, min), max)

const toInteger = (value, fallback, min, max) => {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return fallback
  }
  return clamp(Math.round(parsed), min, max)
}

const baselineFloat32Bytes = (rowCount, dimensions) => rowCount * dimensions * 4

const rawVectorBytes = (rowCount, dimensions, format) => {
  if (format === "BINARY") {
    return rowCount * Math.ceil(dimensions / 8)
  }
  return rowCount * dimensions * (FORMAT_BYTES[format] ?? FORMAT_BYTES.FLOAT32)
}

const indexBytes = (rowCount, dimensions, indexType, hnswM) => {
  if (indexType === "HNSW") {
    return rowCount * hnswM * dimensions * 4
  }
  if (indexType === "IVF") {
    return rowCount * dimensions * 4
  }
  return 0
}

const vectorMemoryBytes = (indexSize, indexType) => {
  if (indexType === "HNSW") {
    return indexSize
  }
  if (indexType === "IVF") {
    return Math.round(indexSize * 0.2)
  }
  return 0
}

export const formatBytes = (bytes) => {
  const normalized = Math.max(Number(bytes) || 0, 0)
  const units = ["B", "KB", "MB", "GB", "TB", "PB"]
  let value = normalized
  let unitIndex = 0
  while (value >= KIB && unitIndex < units.length - 1) {
    value /= KIB
    unitIndex += 1
  }
  const precision = unitIndex === 0 || value >= 10 ? 0 : 1
  return `${value.toFixed(precision)} ${units[unitIndex]}`
}

export const mediaComparisonFor = (bytes) => {
  const normalized = Math.max(Number(bytes) || 0, 0)
  if (normalized <= MEDIA_REFERENCES[0].bytes) {
    return `Fits on one ${MEDIA_REFERENCES[0].label}`
  }
  const reference =
    MEDIA_REFERENCES.find((candidate, index) => {
      const next = MEDIA_REFERENCES[index + 1]
      return next ? normalized <= next.bytes : true
    }) ?? MEDIA_REFERENCES[MEDIA_REFERENCES.length - 1]
  if (!reference) {
    return "Sizing estimate unavailable"
  }
  const count = Math.ceil(normalized / reference.bytes)
  return `${count.toLocaleString()} ${count === 1 ? reference.label : reference.plural}`
}

const vectorMemoryImpact = (bytes) => {
  if (bytes <= 0) {
    return { percent: 0, label: "No Vector memory pool needed" }
  }
  const percent = clamp((bytes / (64 * GIB)) * 100, 4, 100)
  if (bytes < 4 * GIB) {
    return { percent, label: "Modest Vector memory footprint" }
  }
  if (bytes < 16 * GIB) {
    return { percent, label: "Plan a dedicated Vector memory pool" }
  }
  if (bytes < 64 * GIB) {
    return { percent, label: "Large Vector memory allocation" }
  }
  return { percent, label: "Capacity planning required" }
}

export const calculateVectorFootprint = (options = {}) => {
  const rowCount = toInteger(options.rowCount, DEFAULTS.rowCount, ROW_MIN, ROW_MAX)
  const dimensions = toInteger(options.dimensions, DEFAULTS.dimensions, DIMENSION_MIN, DIMENSION_MAX)
  const hnswM = toInteger(options.hnswM, DEFAULTS.hnswM, HNSW_M_MIN, HNSW_M_MAX)
  const format = Object.prototype.hasOwnProperty.call(FORMAT_BYTES, options.format) || options.format === "BINARY" ? options.format : DEFAULTS.format
  const indexType = ["HNSW", "IVF", "NONE"].includes(options.indexType) ? options.indexType : DEFAULTS.indexType
  const rawSize = rawVectorBytes(rowCount, dimensions, format)
  const indexSize = indexBytes(rowCount, dimensions, indexType, hnswM)
  const totalSize = rawSize + indexSize
  const baselineSize = baselineFloat32Bytes(rowCount, dimensions)
  const savingsPercent = clamp((1 - rawSize / baselineSize) * 100, 0, 100)
  const vectorMemory = vectorMemoryBytes(indexSize, indexType)
  const memoryImpact = vectorMemoryImpact(vectorMemory)

  return {
    rowCount,
    dimensions,
    format,
    indexType,
    hnswM,
    rawSize,
    indexSize,
    totalSize,
    baselineSize,
    savingsPercent,
    vectorMemory,
    memoryImpact,
    mediaComparison: mediaComparisonFor(totalSize),
  }
}

const calculatorRoots = (scope) => {
  if (scope instanceof HTMLElement && scope.matches("[data-vector-calculator]")) {
    return [scope]
  }
  return Array.from(scope.querySelectorAll("[data-vector-calculator]"))
}

const inputFor = (root, name) => root.querySelector(`[data-vector-input="${name}"]`)

const syncInputs = (root, name, value) => {
  for (const input of root.querySelectorAll(`[data-vector-input="${name}"]`)) {
    input.value = String(value)
  }
}

const writeOutput = (root, name, value) => {
  for (const output of root.querySelectorAll(`[data-output="${name}"]`)) {
    output.textContent = value
  }
}

const setVisualPercent = (root, name, value) => {
  const visual = root.querySelector(`[data-vector-visual="${name}"]`)
  if (!(visual instanceof HTMLElement)) {
    return
  }
  const percent = clamp(value, 0, 100)
  visual.style.width = `${percent}%`
  visual.setAttribute("aria-valuenow", String(Math.round(percent)))
}

const readState = (root) => ({
  rowCount: inputFor(root, "rowCount")?.value,
  dimensions: inputFor(root, "dimensions")?.value,
  format: inputFor(root, "format")?.value,
  indexType: inputFor(root, "indexType")?.value,
  hnswM: inputFor(root, "hnswM")?.value,
})

const setHnswControls = (root, enabled) => {
  const controls = root.querySelector("[data-hnsw-controls]")
  if (!(controls instanceof HTMLElement)) {
    return
  }
  controls.hidden = !enabled
  for (const input of controls.querySelectorAll("input")) {
    input.disabled = !enabled
  }
}

const renderCalculator = (root) => {
  const estimate = calculateVectorFootprint(readState(root))
  syncInputs(root, "rowCount", estimate.rowCount)
  syncInputs(root, "dimensions", estimate.dimensions)
  syncInputs(root, "hnswM", estimate.hnswM)
  setHnswControls(root, estimate.indexType === "HNSW")

  writeOutput(root, "rowCount", estimate.rowCount.toLocaleString())
  writeOutput(root, "dimensions", estimate.dimensions.toLocaleString())
  writeOutput(root, "hnswM", estimate.hnswM.toLocaleString())
  writeOutput(root, "rawSize", formatBytes(estimate.rawSize))
  writeOutput(root, "indexSize", formatBytes(estimate.indexSize))
  writeOutput(root, "totalSize", formatBytes(estimate.totalSize))
  writeOutput(root, "vectorMemory", formatBytes(estimate.vectorMemory))
  writeOutput(root, "savingsPercent", `${estimate.savingsPercent.toFixed(1)}%`)
  writeOutput(root, "mediaComparison", estimate.mediaComparison)
  writeOutput(root, "memoryImpact", estimate.memoryImpact.label)
  setVisualPercent(root, "compression", estimate.savingsPercent)
  setVisualPercent(root, "vectorMemory", estimate.memoryImpact.percent)
}

const applyPreset = (root, button) => {
  const dimensions = button.dataset.presetDimensions
  const format = button.dataset.presetFormat
  if (dimensions) {
    syncInputs(root, "dimensions", dimensions)
  }
  if (format) {
    syncInputs(root, "format", format)
  }
  renderCalculator(root)
}

const handleInput = (root, event) => {
  const input = event.target instanceof Element ? event.target.closest("[data-vector-input]") : null
  if (!(input instanceof HTMLInputElement || input instanceof HTMLSelectElement)) {
    return
  }
  const name = input.getAttribute("data-vector-input")
  if (name) {
    syncInputs(root, name, input.value)
  }
  renderCalculator(root)
}

export const initVectorCalculator = (scope = document) => {
  for (const root of calculatorRoots(scope)) {
    if (root.dataset.vectorCalculatorReady === "true") {
      continue
    }
    root.dataset.vectorCalculatorReady = "true"
    root.addEventListener("input", (event) => handleInput(root, event))
    root.addEventListener("change", (event) => handleInput(root, event))
    root.addEventListener("click", (event) => {
      const button = event.target instanceof Element ? event.target.closest("[data-vector-preset]") : null
      if (button instanceof HTMLButtonElement) {
        applyPreset(root, button)
      }
    })
    renderCalculator(root)
  }
}

// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

const KIB = 1024
const MIB = KIB ** 2
const GIB = KIB ** 3
const TIB = KIB ** 4

const ROW_MIN = 1_000
const ROW_MAX = 100_000_000
const DIMENSION_MIN = 1
const DIMENSION_MAX = 4_096
const FTS_DOC_BYTES_MIN = 0
const FTS_DOC_BYTES_MAX = 16_384
const HNSW_VECTOR_PAYLOAD_FACTOR = 1.25
const HNSW_GRAPH_BYTES_PER_ROW = 640
const IVF_DISK_INDEX_FACTOR = 1.1
const IVF_CENTROID_OVERHEAD_FACTOR = 3
const FTS_INVERTED_INDEX_RATIO = 0.42
const FTS_MAPPING_BYTES_PER_ROW = 36
const FTS_MIN_SEGMENT_BYTES = 576 * KIB

const DEFAULTS = {
  rowCount: 1_000_000,
  dimensions: 3_072,
  format: "FLOAT32",
  indexType: "HNSW",
  ftsDocBytes: 400,
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

const indexBytes = (rawSize, rowCount, indexType) => {
  if (indexType === "HNSW") {
    return Math.round(rawSize * HNSW_VECTOR_PAYLOAD_FACTOR + rowCount * HNSW_GRAPH_BYTES_PER_ROW)
  }
  if (indexType === "IVF") {
    return Math.round(rawSize * IVF_DISK_INDEX_FACTOR)
  }
  return 0
}

const vectorMemoryBytes = (rawSize, indexSize, rowCount, dimensions, indexType) => {
  if (indexType === "HNSW") {
    return indexSize
  }
  if (indexType === "IVF") {
    const partitions = clamp(Math.floor(Math.sqrt(rowCount)), 1, 65_536)
    const centroidBytes = Math.max(Math.ceil(rawSize / rowCount), dimensions * 4)
    return Math.round(partitions * centroidBytes * IVF_CENTROID_OVERHEAD_FACTOR)
  }
  return 0
}

const ftsIndexBytes = (rowCount, ftsDocBytes) => {
  if (ftsDocBytes <= 0) {
    return 0
  }
  return Math.max(
    FTS_MIN_SEGMENT_BYTES,
    Math.round(rowCount * (ftsDocBytes * FTS_INVERTED_INDEX_RATIO + FTS_MAPPING_BYTES_PER_ROW)),
  )
}

const ftsNoteFor = (ftsDocBytes) => {
  if (ftsDocBytes <= 0) {
    return "CTXSYS.CONTEXT index disabled (0 B/row)."
  }
  return "CTXSYS.CONTEXT ($I postings + $X B-tree + $K/$R IOT) for MULTI_COLUMN_DATASTORE."
}

const indexNoteFor = (indexType, format) => {
  if (indexType === "HNSW") {
    if (format === "INT8" || format === "BINARY") {
      return "HNSW in-memory graph (~1.25x vectors + ~640 B/row neighbor links in Vector Pool)."
    }
    return "HNSW uses Oracle's ~1.3x SGA Vector Pool estimate (vectors + neighbor graph links)."
  }
  if (indexType === "IVF") {
    return "IVF stores ~1.1x partitioned vectors on disk and caches ~sqrt(N) centroids in Vector Pool."
  }
  return "Exact full scan; no vector index or SGA Vector Pool allocation."
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

const vectorMemoryImpact = (bytes, indexType) => {
  if (indexType === "IVF") {
    const percent = bytes > 0 ? clamp((bytes / (4 * GIB)) * 100, 2, 100) : 0
    return {
      percent,
      label: `IVF caches ~sqrt(N) centroids in SGA Vector Pool (${formatBytes(bytes)}); partitions stay on disk`,
    }
  }
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
  const format =
    Object.prototype.hasOwnProperty.call(FORMAT_BYTES, options.format) || options.format === "BINARY"
      ? options.format
      : DEFAULTS.format
  const indexType = ["HNSW", "IVF", "NONE"].includes(options.indexType) ? options.indexType : DEFAULTS.indexType
  const ftsDocBytes = toInteger(options.ftsDocBytes, DEFAULTS.ftsDocBytes, FTS_DOC_BYTES_MIN, FTS_DOC_BYTES_MAX)
  const rawSize = rawVectorBytes(rowCount, dimensions, format)
  const indexSize = indexBytes(rawSize, rowCount, indexType)
  const ftsSize = ftsIndexBytes(rowCount, ftsDocBytes)
  const totalSize = rawSize + indexSize + ftsSize
  const baselineSize = baselineFloat32Bytes(rowCount, dimensions)
  const rawDeltaPercent = (1 - rawSize / baselineSize) * 100
  const savingsPercent = clamp(rawDeltaPercent, 0, 100)
  const savingsLabel =
    rawDeltaPercent < 0 ? `${rawDeltaPercent.toFixed(1)}% (2x FLOAT32)` : `${savingsPercent.toFixed(1)}%`
  const vectorMemory = vectorMemoryBytes(rawSize, indexSize, rowCount, dimensions, indexType)
  const memoryImpact = vectorMemoryImpact(vectorMemory, indexType)

  return {
    rowCount,
    dimensions,
    format,
    indexType,
    ftsDocBytes,
    rawSize,
    indexSize,
    ftsSize,
    totalSize,
    baselineSize,
    savingsPercent,
    savingsLabel,
    vectorMemory,
    memoryImpact,
    indexNote: indexNoteFor(indexType, format),
    ftsNote: ftsNoteFor(ftsDocBytes),
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
  ftsDocBytes: inputFor(root, "ftsDocBytes")?.value,
})

const renderCalculator = (root) => {
  const estimate = calculateVectorFootprint(readState(root))
  syncInputs(root, "rowCount", estimate.rowCount)
  syncInputs(root, "dimensions", estimate.dimensions)
  syncInputs(root, "ftsDocBytes", estimate.ftsDocBytes)

  writeOutput(root, "rowCount", estimate.rowCount.toLocaleString())
  writeOutput(root, "dimensions", estimate.dimensions.toLocaleString())
  writeOutput(root, "ftsDocBytes", `${estimate.ftsDocBytes.toLocaleString()} B`)
  writeOutput(root, "rawSize", formatBytes(estimate.rawSize))
  writeOutput(root, "indexSize", formatBytes(estimate.indexSize))
  writeOutput(root, "ftsSize", formatBytes(estimate.ftsSize))
  writeOutput(root, "totalSize", formatBytes(estimate.totalSize))
  writeOutput(root, "vectorMemory", formatBytes(estimate.vectorMemory))
  writeOutput(root, "savingsPercent", estimate.savingsLabel)
  writeOutput(root, "mediaComparison", estimate.mediaComparison)
  writeOutput(root, "memoryImpact", estimate.memoryImpact.label)
  writeOutput(root, "indexNote", estimate.indexNote)
  writeOutput(root, "ftsNote", estimate.ftsNote)
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

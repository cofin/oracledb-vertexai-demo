// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import ApexCharts from "apexcharts"

const renderEmptyChart = (host, message) => {
  host.replaceChildren()
  const empty = document.createElement("div")
  empty.className = "flex h-full min-h-64 items-center justify-center text-sm font-medium text-muted"
  empty.textContent = message
  host.appendChild(empty)
}

export const initDashboardCharts = async () => {
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

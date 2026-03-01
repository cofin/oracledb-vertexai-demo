import { useQuery } from "@tanstack/react-query"
import { createRoute } from "@tanstack/react-router"
import { ColumnDef, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { useMemo } from "react"

import { apiFetch } from "../lib/http"
import { Route as RootRoute } from "./__root"

type MetricsSummary = {
  total_searches?: number
  avg_search_time_ms?: number
  avg_oracle_time_ms?: number
  avg_similarity_score?: number
}

type ChartsPayload = {
  time_series: {
    labels: string[]
    total_latency: number[]
    oracle_latency: number[]
    vertex_latency: number[]
  }
  breakdown_data: Record<string, unknown>
}

type LatencyRow = {
  label: string
  totalLatencyMs: number
  oracleLatencyMs: number
  vertexLatencyMs: number
}

async function getJson<T>(url: string): Promise<T> {
  const response = await apiFetch(url)
  if (!response.ok) {
    throw new Error(`request failed (${response.status})`)
  }
  return (await response.json()) as T
}

export function PerformancePage() {
  const metricsQuery = useQuery({
    queryKey: ["performance", "metrics"],
    queryFn: () => getJson<MetricsSummary>("/metrics"),
  })
  const chartsQuery = useQuery({
    queryKey: ["performance", "charts"],
    queryFn: () => getJson<ChartsPayload>("/api/metrics/charts"),
  })

  const tableRows = useMemo<LatencyRow[]>(() => {
    const series = chartsQuery.data?.time_series
    if (!series) {
      return []
    }
    return series.labels.map((label, index) => ({
      label,
      totalLatencyMs: series.total_latency[index] ?? 0,
      oracleLatencyMs: series.oracle_latency[index] ?? 0,
      vertexLatencyMs: series.vertex_latency[index] ?? 0,
    }))
  }, [chartsQuery.data])

  const columns = useMemo<ColumnDef<LatencyRow>[]>(
    () => [
      {
        accessorKey: "label",
        header: "Window",
      },
      {
        accessorKey: "totalLatencyMs",
        header: "Total (ms)",
        cell: ({ row }) => row.original.totalLatencyMs.toFixed(1),
      },
      {
        accessorKey: "oracleLatencyMs",
        header: "Oracle (ms)",
        cell: ({ row }) => row.original.oracleLatencyMs.toFixed(1),
      },
      {
        accessorKey: "vertexLatencyMs",
        header: "Vertex (ms)",
        cell: ({ row }) => row.original.vertexLatencyMs.toFixed(1),
      },
    ],
    [],
  )

  const table = useReactTable({
    data: tableRows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  const metrics = metricsQuery.data ?? {}
  const breakdown = chartsQuery.data?.breakdown_data ?? {}
  const loading = metricsQuery.isPending || chartsQuery.isPending

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--text-muted)]">Monitoring</p>
        <h2 className="text-3xl font-semibold tracking-tight text-[var(--text-strong)]">Oracle 26AI Performance</h2>
      </header>

      {loading && <p className="text-sm text-[var(--text-base)]">Loading performance data...</p>}
      {(metricsQuery.error || chartsQuery.error) && (
        <p className="text-sm text-[var(--danger)]">Performance data failed to load.</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4">
          <p className="text-[0.65rem] uppercase tracking-[0.2em] text-[var(--text-muted)]">Total Searches</p>
          <p className="mt-2 text-3xl font-semibold text-[var(--text-strong)]">{metrics.total_searches ?? 0}</p>
        </article>
        <article className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4">
          <p className="text-[0.65rem] uppercase tracking-[0.2em] text-[var(--text-muted)]">Avg Response</p>
          <p className="mt-2 text-3xl font-semibold text-[var(--text-strong)]">
            {(metrics.avg_search_time_ms ?? 0).toFixed(1)}ms
          </p>
        </article>
        <article className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4">
          <p className="text-[0.65rem] uppercase tracking-[0.2em] text-[var(--text-muted)]">Avg Oracle</p>
          <p className="mt-2 text-3xl font-semibold text-[var(--text-strong)]">
            {(metrics.avg_oracle_time_ms ?? 0).toFixed(1)}ms
          </p>
        </article>
        <article className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4">
          <p className="text-[0.65rem] uppercase tracking-[0.2em] text-[var(--text-muted)]">Avg Similarity</p>
          <p className="mt-2 text-3xl font-semibold text-[var(--text-strong)]">
            {(metrics.avg_similarity_score ?? 0).toFixed(3)}
          </p>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4 lg:col-span-2">
          <h3 className="text-sm font-semibold text-[var(--text-strong)]">Latency Timeline</h3>
          <div className="mt-3 overflow-x-auto rounded-xl border border-[var(--border-color)]">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id} className="border-b border-[var(--border-color)] bg-[var(--surface-strong)]">
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="px-3 py-2 text-left font-semibold text-[var(--text-base)]">
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id} className="border-b border-[var(--border-color)]/50">
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-3 py-2 text-[var(--text-base)]">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4">
          <h3 className="text-sm font-semibold text-[var(--text-strong)]">Breakdown</h3>
          <dl className="mt-3 space-y-2 text-sm">
            {Object.entries(breakdown).map(([key, value]) => (
              <div
                key={key}
                className="flex items-start justify-between gap-4 border-b border-[var(--border-color)]/50 pb-2"
              >
                <dt className="text-[var(--text-muted)]">{key}</dt>
                <dd className="text-right text-[var(--text-base)]">{String(value)}</dd>
              </div>
            ))}
            {Object.keys(breakdown).length === 0 && <p className="text-[var(--text-muted)]">No breakdown data yet.</p>}
          </dl>
        </aside>
      </div>
    </section>
  )
}

export const Route = createRoute({
  getParentRoute: () => RootRoute,
  path: "/performance",
  component: PerformancePage,
})

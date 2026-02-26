import { useMemo } from 'react'
import { createRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'

import { Route as RootRoute } from './__root'

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
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`request failed (${response.status})`)
  }
  return (await response.json()) as T
}

function DashboardPage() {
  const metricsQuery = useQuery({
    queryKey: ['dashboard', 'metrics'],
    queryFn: () => getJson<MetricsSummary>('/metrics'),
  })
  const chartsQuery = useQuery({
    queryKey: ['dashboard', 'charts'],
    queryFn: () => getJson<ChartsPayload>('/api/metrics/charts'),
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
        accessorKey: 'label',
        header: 'Window',
      },
      {
        accessorKey: 'totalLatencyMs',
        header: 'Total (ms)',
        cell: ({ row }) => row.original.totalLatencyMs.toFixed(1),
      },
      {
        accessorKey: 'oracleLatencyMs',
        header: 'Oracle (ms)',
        cell: ({ row }) => row.original.oracleLatencyMs.toFixed(1),
      },
      {
        accessorKey: 'vertexLatencyMs',
        header: 'Vertex (ms)',
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
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Complex Dashboard</p>
        <h2 className="text-3xl font-semibold tracking-tight">Search Performance Analytics</h2>
      </header>

      {loading && <p className="text-sm text-zinc-500">Loading dashboard data...</p>}
      {(metricsQuery.error || chartsQuery.error) && (
        <p className="text-sm text-red-600">Dashboard data failed to load.</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-wider text-zinc-500">Total Searches</p>
          <p className="mt-2 text-2xl font-semibold">{metrics.total_searches ?? 0}</p>
        </article>
        <article className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-wider text-zinc-500">Avg Response</p>
          <p className="mt-2 text-2xl font-semibold">{(metrics.avg_search_time_ms ?? 0).toFixed(1)}ms</p>
        </article>
        <article className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-wider text-zinc-500">Avg Oracle</p>
          <p className="mt-2 text-2xl font-semibold">{(metrics.avg_oracle_time_ms ?? 0).toFixed(1)}ms</p>
        </article>
        <article className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-wider text-zinc-500">Avg Similarity</p>
          <p className="mt-2 text-2xl font-semibold">{(metrics.avg_similarity_score ?? 0).toFixed(3)}</p>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="lg:col-span-2 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-zinc-700">Latency Timeline (TanStack Table)</h3>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id} className="border-b border-zinc-200">
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="px-3 py-2 text-left font-semibold text-zinc-700">
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id} className="border-b border-zinc-100">
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-3 py-2 text-zinc-700">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-zinc-700">Breakdown</h3>
          <dl className="mt-3 space-y-2 text-sm">
            {Object.entries(breakdown).map(([key, value]) => (
              <div key={key} className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-2">
                <dt className="text-zinc-500">{key}</dt>
                <dd className="text-right text-zinc-800">{String(value)}</dd>
              </div>
            ))}
            {Object.keys(breakdown).length === 0 && <p className="text-zinc-500">No breakdown data yet.</p>}
          </dl>
        </aside>
      </div>
    </section>
  )
}

export const Route = createRoute({
  getParentRoute: () => RootRoute,
  path: '/dashboard',
  component: DashboardPage,
})

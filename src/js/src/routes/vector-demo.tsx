import { createRoute } from "@tanstack/react-router"
import { FormEvent, useState } from "react"

import { apiFetch } from "../lib/http"
import { Route as RootRoute } from "./__root"

type VectorSearchResult = {
  name: string
  description: string
  similarity: number
  distance: number
}

type VectorDemoResponse = {
  results: VectorSearchResult[]
  search_time_ms: number
  embedding_time_ms: number
  oracle_time_ms: number
  cache_hit: boolean
  performance_level: string
}

function formatMilliseconds(value: number | undefined): string {
  if (typeof value !== "number") {
    return "0.0ms"
  }
  return `${value.toFixed(1)}ms`
}

export function VectorDemoPage() {
  const [query, setQuery] = useState("smooth espresso with chocolate notes")
  const [result, setResult] = useState<VectorDemoResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  async function runVectorSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = query.trim()
    if (!message || isRunning) {
      return
    }

    setError(null)
    setIsRunning(true)

    try {
      const response = await apiFetch("/api/vector-demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: message }),
      })
      if (!response.ok) {
        throw new Error(`vector demo request failed (${response.status})`)
      }
      const payload = (await response.json()) as VectorDemoResponse
      setResult(payload)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "unknown vector demo error")
      setResult(null)
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--text-muted)]">
          Retrieval Playground
        </p>
        <h2 className="text-3xl font-semibold tracking-tight text-[var(--text-strong)]">Vector Search Demo</h2>
        <p className="max-w-3xl text-sm text-[var(--text-base)] md:text-base">
          Query the Cymbal Coffee vectors directly in Oracle 26AI and inspect similarity scoring, embedding latency, and
          search timing.
        </p>
      </header>

      <form
        className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-5 md:p-6"
        onSubmit={runVectorSearch}
      >
        <label className="grid gap-2 text-sm font-medium text-[var(--text-base)]">
          Query
          <input
            className="h-11 rounded-xl border border-[var(--border-color)] bg-[var(--surface-strong)] px-3 text-sm text-[var(--text-strong)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="e.g. fruity light roast for pour-over"
          />
        </label>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            className="inline-flex h-10 items-center justify-center rounded-xl bg-[var(--accent)] px-4 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-50"
            type="submit"
            disabled={isRunning}
          >
            {isRunning ? "Searching..." : "Run Vector Search"}
          </button>
          <p className="text-xs text-[var(--text-muted)]">Enter submits immediately for fast similarity checks.</p>
        </div>
      </form>

      {error && <p className="text-sm text-[var(--danger)]">Error: {error}</p>}

      {result && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <article className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4">
              <p className="text-[0.65rem] uppercase tracking-[0.2em] text-[var(--text-muted)]">Total Time</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--text-strong)]">
                {formatMilliseconds(result.search_time_ms)}
              </p>
            </article>
            <article className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4">
              <p className="text-[0.65rem] uppercase tracking-[0.2em] text-[var(--text-muted)]">Embedding</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--text-strong)]">
                {formatMilliseconds(result.embedding_time_ms)}
              </p>
            </article>
            <article className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4">
              <p className="text-[0.65rem] uppercase tracking-[0.2em] text-[var(--text-muted)]">Oracle Vector</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--text-strong)]">
                {formatMilliseconds(result.oracle_time_ms)}
              </p>
            </article>
            <article className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-4">
              <p className="text-[0.65rem] uppercase tracking-[0.2em] text-[var(--text-muted)]">Cache + Perf</p>
              <p className="mt-2 text-2xl font-semibold capitalize text-[var(--text-strong)]">
                {result.cache_hit ? "Hit" : "Miss"} · {result.performance_level}
              </p>
            </article>
          </div>

          <section className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface)] p-5">
            <h3 className="text-lg font-semibold text-[var(--text-strong)]">Top Similar Matches</h3>
            <div className="mt-4 space-y-3">
              {result.results.map((item, index) => (
                <article
                  key={`${item.name}-${index}`}
                  className="rounded-xl border border-[var(--border-color)] bg-[var(--surface-strong)] p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h4 className="text-base font-semibold text-[var(--text-strong)]">{item.name}</h4>
                    <span className="rounded-full border border-[var(--accent)]/30 bg-[var(--accent-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--accent)]">
                      {item.similarity.toFixed(1)}% similarity
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-[var(--text-base)]">{item.description}</p>
                </article>
              ))}
            </div>
            {result.results.length === 0 && (
              <p className="mt-4 text-sm text-[var(--text-muted)]">No matches returned.</p>
            )}
          </section>
        </>
      )}
    </section>
  )
}

export const Route = createRoute({
  getParentRoute: () => RootRoute,
  path: "/vector-demo",
  component: VectorDemoPage,
})

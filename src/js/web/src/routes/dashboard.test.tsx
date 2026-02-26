import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DashboardPage } from './dashboard'

describe('DashboardPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders metrics cards and latency table', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/metrics') {
        return new Response(
          JSON.stringify({
            total_searches: 24,
            avg_search_time_ms: 55.3,
            avg_oracle_time_ms: 12.7,
            avg_similarity_score: 0.87,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        )
      }
      if (url === '/api/metrics/charts') {
        return new Response(
          JSON.stringify({
            time_series: {
              labels: ['10:00', '10:05'],
              total_latency: [60.1, 58.4],
              oracle_latency: [15.2, 14.1],
              vertex_latency: [22.5, 21.9],
            },
            breakdown_data: {
              product_search: 14,
              store_lookup: 10,
            },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        )
      }
      return new Response('{}', { status: 404 })
    })
    vi.stubGlobal('fetch', fetchMock)

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <DashboardPage />
      </QueryClientProvider>,
    )

    expect(await screen.findByText('24')).toBeInTheDocument()
    expect(screen.getByText('55.3ms')).toBeInTheDocument()
    expect(screen.getByText('12.7ms')).toBeInTheDocument()
    expect(screen.getByText('0.870')).toBeInTheDocument()
    expect(screen.getByText('10:00')).toBeInTheDocument()
    expect(screen.getByText('product_search')).toBeInTheDocument()
  })
})

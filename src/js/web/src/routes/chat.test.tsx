import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ChatPage } from './chat'

describe('ChatPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
  })

  it('sends a message and renders assistant response', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          answer: 'Try our Ethiopia Yirgacheffe.',
          from_cache: false,
          intent_detected: 'PRODUCT_SEARCH',
          search_metrics: {
            response_time_ms: 120.5,
            agent_processing_ms: 88.2,
            search_details: { results_count: 3 },
            products_found: [
              { name: 'Ethiopia Yirgacheffe' },
              { name: 'Kenya AA' },
            ],
            stores_found: [{ name: 'Cymbal Downtown' }],
          },
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    render(<ChatPage />)

    fireEvent.change(screen.getByLabelText('Message'), {
      target: { value: 'Recommend a bright pour-over coffee' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/chat',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-Session-Id': expect.any(String),
        }),
      }),
    )

    expect(await screen.findByText(/Try our Ethiopia Yirgacheffe/)).toBeInTheDocument()
    expect(screen.getByText(/Intent: PRODUCT_SEARCH/)).toBeInTheDocument()
    expect(screen.getByText(/Products: Ethiopia Yirgacheffe, Kenya AA/)).toBeInTheDocument()
    expect(screen.getByText(/Stores: Cymbal Downtown/)).toBeInTheDocument()
    expect(screen.getByText(/Results: 3/)).toBeInTheDocument()
  })
})

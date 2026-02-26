import { FormEvent, useMemo, useState } from 'react'
import { createRoute } from '@tanstack/react-router'

import { Route as RootRoute } from './__root'

type ChatMessage = {
  id: string
  role: 'human' | 'ai' | 'system'
  text: string
}

type ChatReply = {
  answer: string
  from_cache?: boolean
  intent_detected?: string
}

const PERSONAS = ['novice', 'enthusiast', 'expert', 'barista'] as const

const SESSION_STORAGE_KEY = 'coffee-chat-session-id'

function getSessionId() {
  if (typeof window === 'undefined') {
    return 'web-session'
  }
  const existing = window.localStorage.getItem(SESSION_STORAGE_KEY)
  if (existing) {
    return existing
  }
  const created = crypto.randomUUID()
  window.localStorage.setItem(SESSION_STORAGE_KEY, created)
  return created
}

function ChatPage() {
  const sessionId = useMemo(getSessionId, [])
  const [persona, setPersona] = useState<(typeof PERSONAS)[number]>('enthusiast')
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'ai',
      text: 'Ask about coffee products, brewing methods, or nearby stores to start.',
    },
  ])

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = input.trim()
    if (!message || isSending) {
      return
    }

    setError(null)
    setInput('')
    setIsSending(true)

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'human',
      text: message,
    }
    setMessages((previous) => [...previous, userMessage])

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Id': sessionId,
        },
        body: JSON.stringify({ message, persona }),
      })

      if (!response.ok) {
        throw new Error(`chat request failed (${response.status})`)
      }

      const payload = (await response.json()) as ChatReply
      const suffix = payload.from_cache ? ' (cached)' : ''
      const intent = payload.intent_detected ? `\n\nIntent: ${payload.intent_detected}` : ''
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: 'ai',
          text: `${payload.answer}${suffix}${intent}`,
        },
      ])
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'unknown chat error')
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: 'system',
          text: 'Unable to get a response right now. Please retry.',
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Simple Chat</p>
        <h2 className="text-3xl font-semibold tracking-tight">ADK Coffee Assistant</h2>
        <p className="max-w-2xl text-zinc-600">
          Ask the assistant for coffee recommendations, product details, or store information.
        </p>
      </header>

      <div className="grid gap-4 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
        <label className="grid gap-2 text-sm font-medium text-zinc-700">
          Persona
          <select
            className="h-10 rounded-md border border-zinc-300 bg-white px-3 text-sm"
            value={persona}
            onChange={(event) => setPersona(event.target.value as (typeof PERSONAS)[number])}
          >
            {PERSONAS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>

        <div className="h-[420px] space-y-3 overflow-y-auto rounded-lg border border-zinc-200 bg-zinc-50 p-3">
          {messages.map((message) => (
            <article
              key={message.id}
              className={[
                'max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap',
                message.role === 'human' && 'ml-auto bg-zinc-900 text-white',
                message.role === 'ai' && 'mr-auto bg-white text-zinc-900',
                message.role === 'system' && 'mr-auto border border-amber-300 bg-amber-50 text-amber-900',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              {message.text}
            </article>
          ))}
        </div>

        <form className="grid gap-3" onSubmit={sendMessage}>
          <label className="grid gap-2 text-sm font-medium text-zinc-700">
            Message
            <textarea
              className="min-h-24 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm"
              placeholder="Try: recommend a medium roast for pour-over"
              value={input}
              onChange={(event) => setInput(event.target.value)}
            />
          </label>
          <button
            className="inline-flex h-10 items-center justify-center rounded-md bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-50"
            disabled={isSending}
            type="submit"
          >
            {isSending ? 'Sending...' : 'Send'}
          </button>
          {error && <p className="text-sm text-red-600">Error: {error}</p>}
        </form>
      </div>
    </section>
  )
}

export const Route = createRoute({
  getParentRoute: () => RootRoute,
  path: '/chat',
  component: ChatPage,
})

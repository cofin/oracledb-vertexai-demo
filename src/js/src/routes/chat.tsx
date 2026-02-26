import { createRoute } from "@tanstack/react-router"
import { Bot, SendHorizontal, UserRound } from "lucide-react"
import { FormEvent, useEffect, useMemo, useRef, useState } from "react"

import { apiFetch } from "../lib/http"
import { Route as RootRoute } from "./__root"

type ChatMessage = {
  id: string
  role: "human" | "ai" | "system"
  text: string
}

type ChatReply = {
  answer: string
  from_cache?: boolean
  intent_detected?: string
  search_metrics?: {
    response_time_ms?: number
    agent_processing_ms?: number
    search_details?: { results_count?: number }
    products_found?: Array<{ name?: string }>
    stores_found?: Array<{ name?: string }>
  }
}

const PERSONAS = ["novice", "enthusiast", "expert", "barista"] as const

const SESSION_STORAGE_KEY = "coffee-chat-session-id"

function getSessionId() {
  if (typeof window === "undefined") {
    return "web-session"
  }
  const existing = window.localStorage.getItem(SESSION_STORAGE_KEY)
  if (existing) {
    return existing
  }
  const created = crypto.randomUUID()
  window.localStorage.setItem(SESSION_STORAGE_KEY, created)
  return created
}

export function ChatPage() {
  const sessionId = useMemo(getSessionId, [])
  const bottomAnchorRef = useRef<HTMLDivElement | null>(null)
  const hasMountedRef = useRef(false)
  const [persona, setPersona] = useState<(typeof PERSONAS)[number]>("enthusiast")
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "ai",
      text: "Welcome to Connoisseur. Ask for coffee recommendations, product detail, or store lookup.",
    },
  ])

  useEffect(() => {
    const behavior: ScrollBehavior = hasMountedRef.current ? "smooth" : "auto"
    hasMountedRef.current = true
    bottomAnchorRef.current?.scrollIntoView({ behavior, block: "end" })
  }, [])

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = input.trim()
    if (!message || isSending) {
      return
    }

    setError(null)
    setInput("")
    setIsSending(true)

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "human",
      text: message,
    }
    setMessages((previous) => [...previous, userMessage])

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "X-Session-Id": sessionId,
      }
      const response = await apiFetch("/api/chat", {
        method: "POST",
        headers,
        body: JSON.stringify({ message, persona }),
      })

      if (!response.ok) {
        throw new Error(`chat request failed (${response.status})`)
      }

      const payload = (await response.json()) as ChatReply
      const suffix = payload.from_cache ? " (cached)" : ""
      const details: string[] = []

      if (payload.intent_detected) {
        details.push(`Intent: ${payload.intent_detected}`)
      }

      const metrics = payload.search_metrics
      if (metrics) {
        if (typeof metrics.response_time_ms === "number") {
          details.push(`Response: ${Math.round(metrics.response_time_ms)}ms`)
        }
        if (typeof metrics.agent_processing_ms === "number") {
          details.push(`Agent: ${Math.round(metrics.agent_processing_ms)}ms`)
        }
        if (typeof metrics.search_details?.results_count === "number") {
          details.push(`Results: ${metrics.search_details.results_count}`)
        }
        if (metrics.products_found?.length) {
          const names = metrics.products_found
            .map((product) => product.name)
            .filter((name): name is string => Boolean(name))
          if (names.length > 0) {
            details.push(`Products: ${names.join(", ")}`)
          }
        }
        if (metrics.stores_found?.length) {
          const names = metrics.stores_found.map((store) => store.name).filter((name): name is string => Boolean(name))
          if (names.length > 0) {
            details.push(`Stores: ${names.join(", ")}`)
          }
        }
      }

      const context = details.length > 0 ? `\n\n${details.join("\n")}` : ""
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "ai",
          text: `${payload.answer}${suffix}${context}`,
        },
      ])
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "unknown chat error")
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "system",
          text: "Unable to get a response right now. Please retry.",
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  return (
    <section className="grid gap-4 lg:grid-cols-[280px_1fr]">
      <aside className="rounded-3xl border border-zinc-800 bg-zinc-900/80 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-zinc-500">Assistant</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-100">Coffee Chat</h2>
        <p className="mt-2 text-sm text-zinc-400">Select tone, then send a question to the agent.</p>

        <div className="mt-5 grid gap-2">
          {PERSONAS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setPersona(value)}
              className={[
                "rounded-xl border px-3 py-2 text-left text-sm capitalize transition-colors",
                persona === value
                  ? "border-amber-400/60 bg-amber-400/12 text-amber-200"
                  : "border-zinc-700 bg-zinc-950 text-zinc-400 hover:text-zinc-200",
              ].join(" ")}
            >
              {value}
            </button>
          ))}
        </div>
      </aside>

      <div className="rounded-3xl border border-zinc-800 bg-zinc-900/80 p-4 md:p-5">
        <div className="h-[480px] space-y-3 overflow-y-auto rounded-2xl border border-zinc-800 bg-[#0d0f12] p-3 md:p-4">
          {messages.map((message) => (
            <article
              key={message.id}
              className={[
                "max-w-[90%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap md:max-w-[80%]",
                message.role === "human" && "ml-auto border border-amber-500/30 bg-amber-500/15 text-amber-100",
                message.role === "ai" && "mr-auto border border-zinc-700 bg-zinc-900 text-zinc-200",
                message.role === "system" && "mr-auto border border-rose-500/30 bg-rose-500/10 text-rose-200",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <span className="mb-1 flex items-center gap-1 text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                {message.role === "human" ? <UserRound className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                {message.role}
              </span>
              {message.text}
            </article>
          ))}
          <div ref={bottomAnchorRef} />
        </div>

        <form className="mt-4 grid gap-3" onSubmit={sendMessage}>
          <label className="grid gap-2 text-sm font-medium text-zinc-300">
            Message
            <textarea
              className="min-h-24 rounded-2xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500"
              placeholder="Try: Recommend a bold espresso roast"
              value={input}
              onChange={(event) => setInput(event.target.value)}
            />
          </label>
          <button
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-zinc-100 px-4 text-sm font-semibold text-zinc-900 transition-colors hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isSending}
            type="submit"
          >
            <SendHorizontal className="h-4 w-4" />
            {isSending ? "Sending..." : "Send"}
          </button>
          {error && <p className="text-sm text-rose-300">Error: {error}</p>}
        </form>
      </div>
    </section>
  )
}

export const Route = createRoute({
  getParentRoute: () => RootRoute,
  path: "/chat",
  component: ChatPage,
})

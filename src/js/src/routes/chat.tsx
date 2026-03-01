import { createRoute } from "@tanstack/react-router"
import { Bot, Clock, Cpu, Package, SendHorizontal, Store, UserRound, Zap } from "lucide-react"
import { FormEvent, useEffect, useMemo, useRef, useState } from "react"

import { apiFetch } from "../lib/http"
import { Route as RootRoute } from "./__root"

type SearchMetrics = {
  response_time_ms?: number
  agent_processing_ms?: number
  search_details?: { results_count?: number }
  products_found?: Array<{ name?: string }>
  stores_found?: Array<{ name?: string }>
}

type ChatMessage = {
  id: string
  role: "human" | "ai" | "system"
  text: string
  metrics?: SearchMetrics
  fromCache?: boolean
  intent?: string
}

type ChatReply = {
  answer: string
  from_cache?: boolean
  intent_detected?: string
  search_metrics?: SearchMetrics
}

const PERSONAS = ["novice", "enthusiast", "expert", "barista"] as const

const PERSONA_DESCRIPTIONS: Record<(typeof PERSONAS)[number], string> = {
  novice: "Simple, friendly explanations",
  enthusiast: "Balanced detail and passion",
  expert: "Technical, detailed responses",
  barista: "Professional craft perspective",
}

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

function MetricBadge({ icon: Icon, label, value }: { icon: typeof Clock; label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-color)] bg-[var(--surface-strong)] px-2.5 py-1 text-[0.6rem] font-medium text-[var(--text-muted)] transition-colors hover:border-[var(--text-muted)] hover:text-[var(--text-base)]">
      <Icon className="h-3 w-3" />
      <span className="font-semibold text-[var(--text-base)]">{value}</span>
      <span>{label}</span>
    </span>
  )
}

export function ChatPage() {
  const sessionId = useMemo(getSessionId, [])
  const formRef = useRef<HTMLFormElement | null>(null)
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
      text: "Welcome to Cymbal Coffee! Ask me for coffee recommendations, product details, or store locations.",
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
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "ai",
          text: payload.answer,
          metrics: payload.search_metrics,
          fromCache: payload.from_cache,
          intent: payload.intent_detected,
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
    <section className="grid gap-6 lg:grid-cols-[280px_1fr]">
      <aside className="h-fit rounded-3xl border border-[var(--border-color)] bg-[var(--surface)] p-6 shadow-sm">
        <p className="text-[0.65rem] font-bold uppercase tracking-[0.3em] text-[var(--text-muted)]">Gemini Assistant</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-strong)]">Chat</h2>
        <p className="mt-3 text-sm leading-relaxed text-[var(--text-muted)]">
          Pick a tone and ask questions against Oracle-backed product context.
        </p>

        <div className="mt-8 grid gap-2.5">
          {PERSONAS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setPersona(value)}
              className={[
                "rounded-2xl border px-4 py-3.5 text-left transition-all duration-200",
                persona === value
                  ? "border-[var(--accent)]/50 bg-[var(--accent-soft)] text-[var(--text-strong)] ring-1 ring-[var(--accent)]/20 shadow-lg shadow-[var(--accent)]/5"
                  : "border-[var(--border-color)] bg-[var(--surface-strong)] text-[var(--text-muted)] hover:border-[var(--text-muted)]/30 hover:text-[var(--text-base)]",
              ].join(" ")}
            >
              <span className="text-sm font-semibold capitalize">{value}</span>
              <span className="mt-1 block text-[0.7rem] opacity-70 leading-normal">{PERSONA_DESCRIPTIONS[value]}</span>
            </button>
          ))}
        </div>
      </aside>

      <div className="flex flex-col rounded-3xl border border-[var(--border-color)] bg-[var(--surface)] p-4 shadow-sm md:p-6">
        <div className="flex-1 h-[540px] space-y-6 overflow-y-auto rounded-2xl border border-[var(--border-color)] bg-[var(--bg-canvas)]/50 p-4 md:p-6 scrollbar-thin scrollbar-thumb-[var(--surface-soft)]">
          {messages.map((message) => (
            <article
              key={message.id}
              className={[
                "max-w-[90%] md:max-w-[85%]",
                message.role === "human" && "ml-auto",
                message.role !== "human" && "mr-auto",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <div
                className={[
                  "rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-sm transition-all",
                  message.role === "human" && "bg-[var(--accent)] text-white shadow-lg shadow-[var(--accent)]/10",
                  message.role === "ai" &&
                    "border border-[var(--border-color)] bg-[var(--surface-strong)] text-[var(--text-base)]",
                  message.role === "system" &&
                    "border border-[var(--danger)]/30 bg-[var(--danger)]/5 text-[var(--danger)]",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <span
                  className={[
                    "mb-2.5 flex items-center gap-1.5 text-[0.6rem] font-bold uppercase tracking-[0.2em]",
                    message.role === "human" ? "text-white/80" : "text-[var(--text-muted)]",
                  ].join(" ")}
                >
                  {message.role === "human" ? <UserRound className="h-3 w-3" /> : <Bot className="h-3.5 w-3.5" />}
                  {message.role}
                  {message.fromCache && (
                    <span className="ml-1 rounded-full bg-white/20 px-2 py-0.5 text-[0.55rem] font-bold normal-case tracking-normal">
                      cached
                    </span>
                  )}
                </span>
                <div className="whitespace-pre-wrap">{message.text}</div>
              </div>

              {message.role === "ai" && message.metrics && (
                <div className="mt-3 flex flex-wrap gap-2 px-1">
                  {typeof message.metrics.response_time_ms === "number" && (
                    <MetricBadge
                      icon={Clock}
                      label="latency"
                      value={`${Math.round(message.metrics.response_time_ms)}ms`}
                    />
                  )}
                  {typeof message.metrics.agent_processing_ms === "number" && (
                    <MetricBadge
                      icon={Cpu}
                      label="agent"
                      value={`${Math.round(message.metrics.agent_processing_ms)}ms`}
                    />
                  )}
                  {message.metrics.products_found && message.metrics.products_found.length > 0 && (
                    <MetricBadge
                      icon={Package}
                      label="products"
                      value={String(message.metrics.products_found.length)}
                    />
                  )}
                  {message.metrics.stores_found && message.metrics.stores_found.length > 0 && (
                    <MetricBadge icon={Store} label="stores" value={String(message.metrics.stores_found.length)} />
                  )}
                  {message.intent && message.intent !== "GENERAL_CONVERSATION" && (
                    <MetricBadge icon={Zap} label="" value={message.intent.toLowerCase().replace("_", " ")} />
                  )}
                </div>
              )}
            </article>
          ))}
          <div ref={bottomAnchorRef} />
        </div>

        <form ref={formRef} className="mt-6 space-y-4" onSubmit={sendMessage}>
          <div className="relative">
            <textarea
              className="w-full min-h-[100px] rounded-2xl border border-[var(--border-color)] bg-[var(--surface-strong)] px-4 py-4 text-sm text-[var(--text-strong)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]/50 focus:outline-none focus:ring-1 focus:ring-[var(--accent)]/50 transition-all resize-none"
              placeholder="Try: Find medium-roast chocolate notes under $20"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  formRef.current?.requestSubmit()
                }
              }}
            />
            <div className="absolute right-3 bottom-3 flex items-center gap-4">
              <span className="hidden sm:block text-[0.65rem] font-medium text-[var(--text-muted)]">
                <kbd className="rounded bg-[var(--surface-soft)] px-1 py-0.5 text-[var(--text-base)]">↵</kbd> to send
              </span>
              <button
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)] text-white shadow-lg shadow-[var(--accent)]/20 transition-all hover:bg-[var(--accent-strong)] hover:scale-105 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:grayscale"
                disabled={isSending}
                type="submit"
              >
                <SendHorizontal className="h-5 w-5" />
                <span className="sr-only">Send</span>
              </button>
            </div>
          </div>
          {error && <p className="text-xs font-medium text-[var(--danger)] ml-1">Error: {error}</p>}
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

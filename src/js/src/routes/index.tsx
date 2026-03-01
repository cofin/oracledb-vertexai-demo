import { createRoute, Link } from "@tanstack/react-router"
import { Activity, FlaskConical, type LucideIcon, MessageCircleMore, Sparkles } from "lucide-react"

import { Route as RootRoute } from "./__root"

type Tile = {
  title: string
  description: string
  href?: string
  status: "live" | "soon"
  icon: LucideIcon
}

const tiles: Tile[] = [
  {
    title: "Gemini Chat Console",
    description: "Chat-driven recommendations powered by Gemini and Oracle 26AI context retrieval.",
    href: "/chat",
    status: "live",
    icon: MessageCircleMore,
  },
  {
    title: "Performance Monitor",
    description: "Inspect endpoint timing, Oracle vector latency, and retrieval health.",
    href: "/performance",
    status: "live",
    icon: Activity,
  },
  {
    title: "Vector Search Demo",
    description: "Run semantic similarity queries directly against Oracle 26AI vectors.",
    href: "/vector-demo",
    status: "live",
    icon: FlaskConical,
  },
  {
    title: "Agent Workbench",
    description: "Prompt orchestration and tool chains for richer Gemini workflows.",
    status: "soon",
    icon: Sparkles,
  },
]

export function LandingPage() {
  return (
    <section className="space-y-12">
      <header className="max-w-2xl space-y-5">
        <p className="text-[0.65rem] font-bold uppercase tracking-[0.3em] text-[var(--accent)]">Demo Control Plane</p>
        <h2 className="text-4xl font-semibold tracking-tight text-[var(--text-strong)] sm:text-5xl lg:text-6xl">
          Oracle 26AI Vector <br />
          <span className="text-[var(--text-muted)]">& Gemini Orchestration</span>
        </h2>
        <p className="text-base leading-relaxed text-[var(--text-base)] md:text-lg">
          Explore semantic search, RAG workflows, and performance metrics across the Cymbal Coffee dataset.
        </p>
      </header>

      <div className="grid gap-5 sm:grid-cols-2">
        {tiles.map((tile) => {
          const Icon = tile.icon
          const commonClass =
            "group relative overflow-hidden rounded-3xl border border-[var(--border-color)] bg-[var(--surface)] p-8 transition-all duration-300 hover:border-[var(--surface-soft)] hover:bg-[var(--surface-strong)] hover:shadow-2xl hover:shadow-black/50"

          const content = (
            <>
              <div className="absolute -right-12 -top-12 h-40 w-40 rounded-full bg-[var(--accent)]/5 blur-3xl transition-opacity group-hover:opacity-100" />
              <div className="relative flex h-full flex-col gap-8">
                <div className="flex items-start justify-between gap-4">
                  <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border-color)] bg-[var(--bg-canvas)] text-[var(--text-strong)] transition-colors group-hover:border-[var(--accent)]/30 group-hover:bg-[var(--accent-soft)]">
                    <Icon
                      className="h-7 w-7 transition-transform duration-300 group-hover:scale-110"
                      aria-hidden="true"
                    />
                  </span>
                  <span
                    className={[
                      "rounded-full px-3 py-1 text-[0.6rem] font-bold uppercase tracking-[0.2em]",
                      tile.status === "live"
                        ? "border border-[var(--success)]/20 bg-[var(--success)]/10 text-[var(--success)]"
                        : "border border-[var(--border-color)] bg-[var(--surface-strong)] text-[var(--text-muted)]",
                    ].join(" ")}
                  >
                    {tile.status === "live" ? "Live" : "Soon"}
                  </span>
                </div>
                <div className="space-y-3">
                  <h3 className="text-xl font-semibold text-[var(--text-strong)]">{tile.title}</h3>
                  <p className="text-sm leading-relaxed text-[var(--text-muted)] group-hover:text-[var(--text-base)]">
                    {tile.description}
                  </p>
                </div>
              </div>
            </>
          )

          if (tile.href) {
            return (
              <Link key={tile.title} to={tile.href} className={commonClass}>
                {content}
              </Link>
            )
          }

          return (
            <article key={tile.title} className={`${commonClass} opacity-60 grayscale-[0.5]`} aria-disabled="true">
              {content}
            </article>
          )
        })}
      </div>
    </section>
  )
}

export const Route = createRoute({
  getParentRoute: () => RootRoute,
  path: "/",
  component: LandingPage,
})

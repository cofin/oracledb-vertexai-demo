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
    title: "Chat Interface",
    description: "Talk with the coffee assistant in real time.",
    href: "/chat",
    status: "live",
    icon: MessageCircleMore,
  },
  {
    title: "Performance Monitor",
    description: "Inspect latency and vector search health.",
    href: "/performance",
    status: "live",
    icon: Activity,
  },
  {
    title: "Coffee Library",
    description: "Product intelligence modules are queued.",
    status: "soon",
    icon: FlaskConical,
  },
  {
    title: "Automation Studio",
    description: "Workflow orchestration panel coming next.",
    status: "soon",
    icon: Sparkles,
  },
]

export function LandingPage() {
  return (
    <section className="space-y-8 md:space-y-10">
      <header className="max-w-3xl space-y-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">Dashboard Landing</p>
        <h2 className="text-4xl font-semibold tracking-tight text-zinc-100 sm:text-5xl">Coffee Operations Command</h2>
        <p className="text-base leading-relaxed text-zinc-400 md:text-lg">
          A minimal dark workspace for chat and performance workflows. Start with the core tools below.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        {tiles.map((tile) => {
          const Icon = tile.icon
          const commonClass =
            "group relative overflow-hidden rounded-3xl border border-zinc-800 bg-zinc-900/70 p-6 transition duration-300 motion-safe:hover:-translate-y-0.5 motion-safe:hover:border-zinc-600 motion-safe:hover:shadow-[0_20px_50px_-28px_rgba(245,158,11,0.5)]"

          const content = (
            <>
              <div className="absolute -right-10 -top-10 h-36 w-36 rounded-full bg-zinc-800/60 blur-2xl transition group-hover:bg-amber-500/20" />
              <div className="relative flex h-full flex-col gap-6">
                <div className="flex items-start justify-between gap-4">
                  <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-zinc-700 bg-zinc-950 text-zinc-200">
                    <Icon className="h-7 w-7" aria-hidden="true" />
                  </span>
                  <span
                    className={[
                      "rounded-full px-2.5 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.2em]",
                      tile.status === "live"
                        ? "border border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
                        : "border border-zinc-600 bg-zinc-800 text-zinc-300",
                    ].join(" ")}
                  >
                    {tile.status === "live" ? "Live" : "Soon"}
                  </span>
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold text-zinc-100">{tile.title}</h3>
                  <p className="text-sm text-zinc-400">{tile.description}</p>
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
            <article key={tile.title} className={commonClass} aria-disabled="true">
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

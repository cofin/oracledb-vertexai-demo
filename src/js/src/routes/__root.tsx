import { createRootRoute, Link, Outlet } from "@tanstack/react-router"

const navigation = [
  { to: "/", label: "Home" },
  { to: "/chat", label: "Chat" },
  { to: "/performance", label: "Performance" },
] as const

function RootLayout() {
  return (
    <div className="min-h-screen bg-[#0a0b0d] text-zinc-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(245,158,11,0.16),_transparent_38%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.12),_transparent_42%)]" />
      <header className="sticky top-0 z-30 border-b border-zinc-800/80 bg-[#0a0b0d]/85 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-4 md:px-8">
          <div>
            <p className="text-[0.62rem] font-semibold uppercase tracking-[0.24em] text-amber-300/70">Cymbal Coffee</p>
            <h1 className="text-base font-semibold tracking-tight text-zinc-100">Connoisseur</h1>
          </div>
          <nav className="flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/60 p-1 text-sm">
            {navigation.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="rounded-full px-3 py-1.5 text-zinc-400 transition-colors hover:text-zinc-100 [&.active]:bg-zinc-100 [&.active]:text-zinc-900"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="relative mx-auto w-full max-w-6xl px-5 py-8 md:px-8 md:py-10">
        <Outlet />
      </main>
    </div>
  )
}

export const Route = createRootRoute({
  component: RootLayout,
})

import { Link, Outlet, createRootRoute } from '@tanstack/react-router'

function RootLayout() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <header className="border-b border-zinc-200 bg-white/95">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold tracking-tight">Cymbal Coffee</h1>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/" className="[&.active]:font-semibold">
              Home
            </Link>
            <Link to="/chat" className="[&.active]:font-semibold">
              Chat
            </Link>
            <Link to="/dashboard" className="[&.active]:font-semibold">
              Dashboard
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}

export const Route = createRootRoute({
  component: RootLayout,
})

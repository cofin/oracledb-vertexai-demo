import { createRootRoute, Link, Outlet } from "@tanstack/react-router"
import { Moon, Sun } from "lucide-react"
import { useEffect, useState } from "react"

const navigation = [
  { to: "/", label: "Home" },
  { to: "/chat", label: "Chat" },
  { to: "/vector-demo", label: "Vector Demo" },
  { to: "/performance", label: "Performance" },
] as const

function useTheme() {
  const [dark, setDark] = useState(() => localStorage.getItem("theme") !== "light")

  useEffect(() => {
    document.documentElement.classList.toggle("light", !dark)
    localStorage.setItem("theme", dark ? "dark" : "light")
  }, [dark])

  return [dark, () => setDark((d) => !d)] as const
}

function RootLayout() {
  const [dark, toggleTheme] = useTheme()

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--text-base)]">
      <header className="sticky top-0 z-30 border-b border-[var(--border-color)] bg-[var(--bg-canvas)]/80 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-3 md:px-8">
          <Link to="/" className="flex items-center gap-3 transition-opacity hover:opacity-80">
            <span className="overflow-hidden rounded-lg border border-[var(--border-color)] bg-white p-1">
              <img src="/cymbal-orig.jpg" alt="Cymbal Coffee" width={94} height={32} className="h-7 w-auto md:h-8" />
            </span>
            <div className="hidden sm:block">
              <p className="text-[0.6rem] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                Cymbal Coffee
              </p>
              <h1 className="text-sm font-semibold tracking-tight text-[var(--text-strong)]">Oracle 26AI + Gemini</h1>
            </div>
          </Link>
          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1 rounded-full border border-[var(--border-color)] bg-[var(--surface-strong)] p-1 text-[0.8rem] font-medium">
              {navigation.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className="rounded-full px-3.5 py-1.5 text-[var(--text-muted)] transition-all hover:text-[var(--text-strong)] [&.active]:bg-[var(--surface-soft)] [&.active]:text-[var(--text-strong)] [&.active]:shadow-sm"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            <button
              type="button"
              onClick={toggleTheme}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-[var(--border-color)] bg-[var(--surface-strong)] text-[var(--text-muted)] transition-all hover:text-[var(--text-strong)]"
              title={dark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>
      </header>
      <main className="relative mx-auto w-full max-w-6xl px-5 py-8 md:px-8 md:py-12">
        <Outlet />
      </main>
    </div>
  )
}

export const Route = createRootRoute({
  component: RootLayout,
})

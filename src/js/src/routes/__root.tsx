import { createRootRoute, Link, Outlet } from "@tanstack/react-router"
import { Moon, Sun } from "lucide-react"
import { useEffect, useState } from "react"

import { CymbalLogo } from "../components/CymbalLogo"
import { RetroGrid } from "../components/RetroGrid"

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
            <CymbalLogo className="h-8 w-auto md:h-10" />
          </Link>
          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1 rounded-full border border-[var(--border-color)] bg-[var(--surface-strong)] p-1 text-[0.8rem] font-semibold">
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
        <RetroGrid className="fixed inset-0" />
        <div className="relative z-10">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export const Route = createRootRoute({
  component: RootLayout,
})

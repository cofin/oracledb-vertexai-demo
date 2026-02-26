import { createRoute } from '@tanstack/react-router'

import { Route as RootRoute } from './__root'

function HomePage() {
  return (
    <section className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">ADK Dashboard</p>
      <h2 className="text-3xl font-semibold tracking-tight">Frontend Route Shell Ready</h2>
      <p className="max-w-2xl text-zinc-600">
        This route tree scaffold is ready for the task-specific chat and dashboard interfaces.
      </p>
    </section>
  )
}

export const Route = createRoute({
  getParentRoute: () => RootRoute,
  path: '/',
  component: HomePage,
})

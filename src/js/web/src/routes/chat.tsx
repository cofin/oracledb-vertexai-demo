import { createRoute } from '@tanstack/react-router'

import { Route as RootRoute } from './__root'

function ChatPage() {
  return (
    <section className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Route</p>
      <h2 className="text-3xl font-semibold tracking-tight">Chat</h2>
      <p className="max-w-2xl text-zinc-600">
        Simple ADK chat interface will be implemented in the next UI task.
      </p>
    </section>
  )
}

export const Route = createRoute({
  getParentRoute: () => RootRoute,
  path: '/chat',
  component: ChatPage,
})

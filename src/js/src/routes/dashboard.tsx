import { createRoute, redirect } from "@tanstack/react-router"

import { Route as RootRoute } from "./__root"

export const Route = createRoute({
  getParentRoute: () => RootRoute,
  path: "/dashboard",
  beforeLoad: () => {
    throw redirect({ to: "/performance" })
  },
})

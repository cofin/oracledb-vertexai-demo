import { Route as RootRoute } from "./routes/__root"
import { Route as ChatRoute } from "./routes/chat"
import { Route as DashboardRoute } from "./routes/dashboard"
import { Route as IndexRoute } from "./routes/index"
import { Route as PerformanceRoute } from "./routes/performance"

const routeTree = RootRoute.addChildren([IndexRoute, ChatRoute, PerformanceRoute, DashboardRoute])

export { routeTree }

import { Route as RootRoute } from './routes/__root'
import { Route as ChatRoute } from './routes/chat'
import { Route as DashboardRoute } from './routes/dashboard'
import { Route as IndexRoute } from './routes/index'

const routeTree = RootRoute.addChildren([IndexRoute, ChatRoute, DashboardRoute])

export { routeTree }

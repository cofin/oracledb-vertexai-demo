# Flow: ADK Chat & Dashboard (adk-chat-dashboard_20260225)

## 1. Product Requirements Document (PRD)

### 1.1 Goal
Port the modern frontend architecture from the `accelerator` project into `oracledb-vertexai-demo` to replace the HTMX application. Build a modern, full-stack application featuring a simple, intuitive chat interface powered by Google ADK (Agent Development Kit) and `google.genai`, along with a secondary, more complex dashboard page. 

### 1.2 Key Features
1. **Frontend Architecture Bootstrapping**: Introduce `litestar-vite`, `react` 19, `bun`, `tanstack`, and `shadcn` into the existing `oracledb-vertexai-demo` repository.
2. **Dependency Exclusion**: Use `uv` overrides in `pyproject.toml` to prevent the installation of legacy ADK dependencies (`fastapi`, `starlette`, `sqlalchemy`, `alembic`).
3. **Simple Chat Interface (Page 1)**: A clean, user-friendly chat interface for interacting with a Google ADK agent. Includes an input field, message list (user vs. agent), and auto-scrolling. 
4. **Complex Dashboard (Page 2)**: A sophisticated data view displaying chat history, agent usage metrics, or system status. It leverages `TanStack Table` (`ServerSideDataTable` component) for server-side pagination, sorting, and filtering. Includes data fetching mapped directly to Litestar generated endpoints (`@/lib/generated/api/@tanstack/react-query.gen`). Utilizes Shadcn components (`Card`, `Status`, `AvatarGroup`, `Dropzone`) for advanced layouts.
5. **Backend Architecture**: Explicit DI configuration in `app/ioc.py`, `app/lib/di.py` and `app/config.py` to wire up new ADK Domain Services using the existing Dishka container.

### 1.3 Architecture & Tech Stack
- **Backend**: Python 3.12+, Litestar, SQLSpec (Asyncpg/DuckDB/OracleDB), Dishka (DI), Google ADK (`google.adk.agents.Agent`) + `google.genai`.
- **Frontend**: React 19, Bun, Vite, TanStack Router/Query/Table, Tailwind CSS v4, Shadcn UI.
- **Persistence**: ADK sessions and events are natively managed via `sqlspec.extensions.adk.SQLSpecSessionService` and backed by `OracleAsyncADKStore`. By adding `extension_config={"adk": {"in_memory": True}}` to the database config in `config.py`, standard database migrations automatically configure the tables, complete with `INMEMORY PRIORITY HIGH` optimizations on Oracle.

## 2. Implementation Plan

### Phase 0: HTMX Code & Template Removal
To cleanly transition to the modern React/Vite stack, the following legacy HTMX code and template artifacts must be completely removed from the project:

**Files to Delete:**
- **Templates**: `app/server/templates/coffee_chat.html`, `app/server/templates/performance_dashboard.html`, and the entire `app/server/templates/partials/` directory.
- **Static Assets**: All HTMX-specific Javascript in `app/server/static/js/` (`chat-streaming.js`, `help-tooltips-htmx.js`, `tooltip-positioning.js`, `simple-tooltip-positioning.js`).

**Code to Refactor/Remove:**
- **`app/server/plugins.py`**: Remove `from litestar.plugins.htmx import HTMXPlugin` and the `htmx = HTMXPlugin()` instantiation.
- **`app/server/core.py`**: Remove `HTMXRequest` imports and remove `app_config.request_class = HTMXRequest`.
- **`app/server/exception_handlers.py`**: Delete `HTMXValidationException`, `HTMXAPIException`, and all related handler functions (`handle_validation_exception`, `handle_htmx_api_exception`, etc.) that return `HTMXTemplate`.
- **`app/server/controllers.py`**:
  - Remove all `HTMXRequest` and `HTMXTemplate` imports.
  - Delete `show_coffee_chat` and `performance_dashboard` routes (these will be handled by React Router).
  - Refactor `handle_coffee_chat` and `stream_response` to return pure JSON/SSE data instead of `HTMXTemplate` wrapping HTML chunks.
  - Delete endpoints serving HTML partials like `vector_search_demo` (if returning HTML) and `get_metrics_summary`.

### Phase 1: Environment & Dependency Setup
- [ ] Task 1: Update `pyproject.toml` with `uv` overrides for `fastapi`, `starlette`, `sqlalchemy`, `alembic` to use dummy/empty packages.
- [ ] Task 2: Install or update `google-adk` and `google-genai` and verify no legacy dependencies leaked into the environment.

### Phase 2: Database & Backend Services (SQLSpec & Litestar)
- [ ] Task 3.1: Update `app/config.py` to add `"adk": {"in_memory": True}` inside the `extension_config` of `DatabaseConfig` so the standard migration system natively creates the required `adk_sessions` and `adk_events` tables.
- [ ] Task 4.1: Configure Dishka Dependency Injection in `app/ioc.py` and `app/lib/di.py` to provide the `OracleAsyncADKStore` and the `SQLSpecSessionService`.
- [ ] Task 5: Implement the Litestar `ChatController` to inject `SQLSpecSessionService`. Map routes for creating sessions and retrieving session histories.
- [ ] Task 6: Integrate Google ADK Agent (`google.adk.agents.Agent`) within the `ChatController` by passing the injected `SQLSpecSessionService` to natively persist conversations.

### Phase 3: Frontend Bootstrapping (Litestar-Vite & React)
- [ ] Task 7.1: Add `litestar-vite` to `pyproject.toml` dependencies.
- [ ] Task 7.2: Implement `ViteSettings` in `app/lib/settings.py` and instantiate `ViteConfig` in `app/config.py`. Register `VitePlugin` in `app/server/plugins.py`.
- [ ] Task 7.3: Scaffold `src/js/web` directory. Create `package.json` (React, Bun, TanStack, Shadcn, Tailwind), `vite.config.ts`, `tsconfig.json`, and `tailwind.config.js`.

### Phase 4: Frontend Setup & Routing (TanStack)
- [ ] Task 8.1: Run `litestar assets generate-types` (or configure OpenAPI TS generation) to create TanStack Query hooks.
- [ ] Task 8.2: Scaffold TanStack Router file-based route tree (`src/routes/__root.tsx`, `src/routes/chat.tsx`, `src/routes/dashboard.tsx`).

### Phase 5: UI Implementation (React & Shadcn)
- [ ] Task 9: Build the Simple Chat Interface (`/chat`). Utilize Shadcn components (`Card`, `Input`, `Button`, `ScrollArea`, `Avatar`) for the layout. Integrate generated `useMutation` hooks to stream/send messages.
- [ ] Task 10: Build the Complex Dashboard (`/dashboard`). Implement the `ServerSideDataTable` component. Display paginated, sorted server-side data (metrics/history). Add Shadcn UI status indicators.

### Phase 6: Testing & Quality Gate
- [ ] Task 11: Write Pytest unit/integration tests for the backend (ADK integration).
- [ ] Task 12: Write Vitest tests for frontend components.
- [ ] Task 13: Run `make test`, `make lint`, and verify zero style errors.

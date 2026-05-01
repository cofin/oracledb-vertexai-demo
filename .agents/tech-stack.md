# Technology Stack

<!-- truth: start -->
## Backend

- **Language:** Python 3.12+ (managed via `uv`)
- **Framework:** Litestar
- **Server:** Litestar-granian (ASGI server)
- **Dependency Injection:** Dishka
- **AI & Integrations:** Google Vertex AI, Google ADK 2.0, SQLSpec ADK session
  service

## Frontend

- **Framework:** HTMX + Jinja templates, Alpine.js
- **Charts:** ApexCharts
- **Build Tool:** Vite (integrated via `litestar-vite`)
- **Styling:** Tailwind CSS

## Data & Persistence

- **Database:** Oracle Database 26ai (Vector Search, RAG)
- **Data Access:** SQLSpec (with `python-oracledb` and `mypyc` optimizations)
- **Browser Sessions:** Litestar server-side sessions backed by SQLSpec Oracle
  storage
- **Agent Sessions:** SQLSpec Oracle ADK store (`adk_sessions`, `adk_events`,
  optional memory tables)

## Chat Runner Flow

- `/` hydrates the anonymous browser's ADK-backed display history through the
  Litestar session bridge.
- `/api/chat/stream` is the primary chat route. It checks response cache,
  classifies intent, runs direct grounded product lookup for `PRODUCT_RAG`, and
  runs ADK SSE streaming for non-RAG model conversation.
- Product/menu answers are formatted only from returned Cymbal Coffee menu rows.
  They emit a final SSE event without speculative model deltas.
- The sidebar `Clear chat` action deletes the current ADK session/events and
  clears the Litestar bridge keys; it does not reset caches, metrics, fixtures,
  or product data.

## Tooling & Infrastructure

- **Python Package Management:** `uv`
- **JavaScript Package Management:** `bun`
- **Hook Management & Pre-commit:** `prek` (Rust-based fast runner)
- **Linting & Formatting:** Ruff (Python), Biome (JavaScript/TypeScript)
<!-- truth: end -->

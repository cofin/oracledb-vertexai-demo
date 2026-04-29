# Technology Stack

<!-- truth: start -->
## Backend

- **Language:** Python 3.12+ (managed via `uv`)
- **Framework:** Litestar
- **Server:** Litestar-granian (ASGI server)
- **Dependency Injection:** Dishka
- **AI & Integrations:** Google Vertex AI, Google ADK

## Frontend

- **Framework:** React, TypeScript
- **Routing:** TanStack Router
- **Build Tool:** Vite (integrated via `litestar-vite`)
- **Styling:** Tailwind CSS

## Data & Persistence

- **Database:** Oracle Database 23ai (Vector Search, RAG)
- **Data Access:** SQLSpec (with `python-oracledb` and `mypyc` optimizations)

## Tooling & Infrastructure

- **Python Package Management:** `uv`
- **JavaScript Package Management:** `bun`
- **Hook Management & Pre-commit:** `prek` (Rust-based fast runner)
- **Linting & Formatting:** Ruff (Python), Biome (JavaScript/TypeScript)
<!-- truth: end -->

# Technology Stack

<!-- truth: start -->
## Backend
- **Language:** Python 3.12+ (managed via `uv`)
- **Framework:** Litestar
- **Server:** Granian (wired via `litestar-granian`)
- **Dependency Injection:** Dishka
- **AI:** Google Vertex AI & Google ADK 2 (`google-adk>=2.0.0`)

## Frontend
- **Framework:** HTMX 2.x + Jinja2 templates (no React/SPA)
- **Asset Pipeline:** Vite (wired via `litestar-vite`)
- **Styling:** Tailwind CSS v4
- **Charts:** ApexCharts

## Persistence
- **Database:** Oracle Database 26ai (Vector Search, HNSW)
- **Data Access:** SQLSpec (with `python-oracledb` and `mypyc`)
- **Browser Sessions:** Server-side sessions in Oracle
- **Agent Sessions:** SQLSpec Oracle ADK session store

## Tooling
- **Package Managers:** `uv` (Python), `npm` (JS)
- **VCS Hook Runner:** `prek`
- **Lint/Format:** Ruff (Python), TypeScript compiler check
<!-- truth: end -->

For detailed component mappings, see [guides/architecture.md](knowledge/guides/architecture.md).

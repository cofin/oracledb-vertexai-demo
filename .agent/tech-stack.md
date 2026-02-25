# Technology Stack

## Backend
- **Language:** Python 3.12+
- **Framework:** [Litestar](https://litestar.dev/) - High-performance, asynchronous Python web framework.
- **Dependency Injection:** [Dishka](https://github.com/T0_0T/dishka) - Clean and powerful DI container.

## AI & Data
- **Database:** **Oracle Database 23ai** - Native vector similarity search, JSON Relational Duality, and ACID transactions.
- **Database Access:** [SQLSpec](https://github.com/litestar-org/sqlspec) with `python-oracledb` - Type-safe, named SQL query mapper optimized for Oracle.
- **AI Platform:** **Google Vertex AI** - Used for text embeddings (text-embedding-005) and generative chat responses (Gemini 2.5 Flash).
- **Agent Framework:** **Google ADK** - For building structured agentic workflows and tool integrations.

## Frontend & Assets
- **Templating:** Jinja2
- **Interactivity:** [HTMX](https://htmx.org/) - Hypermedia-driven UI updates.
- **Styling:** Tailwind CSS (Modern, clean, and polished aesthetic).
- **Asset Pipeline:** [Litestar-Vite](https://github.com/litestar-org/litestar-vite) - Modern bundling and Vite integration.

## Development & Quality
- **Package Manager:** [uv](https://github.com/astral-sh/uv) - Extremely fast Python package and environment manager.
- **Linting & Formatting:** Ruff
- **Type Checking:** MyPy / Pyright
- **Testing:** Pytest (with `pytest-asyncio` and `pytest-databases`)

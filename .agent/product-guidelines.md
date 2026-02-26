# Product Guidelines

## Core Mandates
- **Reference Standard:** Code must be a primary example of "how to do it right" for Oracle 23ai + Vertex AI. It must be polished, production-ready, and fully annotated.
- **Simplicity:** Prefer readable, straightforward logic over complex abstractions. Do not use defensive code (`hasattr`, `getattr`) when Protocols and proper types can be used.
- **Conciseness:** Avoid boilerplate and redundant code.
- **No Dead Code:** Unused imports, variables, and functions MUST be removed.
- **Correctness:** Full type hints (`mypy --strict` compliant) and rigorous validation are required. Error messages must be lowercase without trailing periods.

## Architectural Principles
- **Service Layer:** All business logic lives in `app/services/`. Routing layer (Controllers) must be extremely thin, delegating to Services.
- **Repository Pattern:** Database access is isolated in repositories utilizing SQLSpec. Services should never expose raw driver cursors.
- **HTMX First:** Prioritize server-side interactivity with minimal client-side JavaScript. Litestar endpoints should return HTML fragments rendered via Jinja2 for HTMX swapping.
- **Async Everywhere:** Use `async/await` for all I/O and non-blocking operations.
- **Dependency Injection:** Use Dishka for wiring configurations, services, database connection pools, and Vertex AI clients.

## UI/UX Standards
- **Clean Aesthetics:** Use Tailwind CSS for a modern, clean, and polished aesthetic.
- **Real-time Feedback:** Use HTMX for interactive elements like chat and search.
- **Performance:** Aim for low latency; use Oracle-backed caching for embeddings and responses.
- **Asset Pipeline:** Utilize **Litestar-Vite** for modern frontend bundling and HMR.

## Agent System Standards
- **Cleanup Mandatory:** The Review Phase/Docs & Vision Agent MUST clean all `tmp/` directories and archive completed requirements to `.agent/archive/` (previously `specs/archive/`).
- **Research First:** Always check `.agent/knowledge/guides/` before executing external research.

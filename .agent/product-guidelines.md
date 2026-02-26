# Product Guidelines

## Core Mandates
- **Reference Standard:** Code must be a primary example of "how to do it right" for Oracle 23ai + Vertex AI. It must be polished, production-ready, and fully annotated.
- **Simplicity:** Prefer readable, straightforward logic over complex abstractions. Do not use defensive code (`hasattr`, `getattr`) when Protocols and proper types can be used.
- **Conciseness:** Avoid boilerplate and redundant code.
- **No Dead Code:** Unused imports, variables, and functions MUST be removed.
- **Correctness:** Full type hints (`mypy --strict` compliant) and rigorous validation are required. Error messages must be lowercase without trailing periods.

## Architecture Standards
- **Domain-Driven Layout:** Organize code under `app/domain/<domain>/` with domain-local `controllers`, `services`, `schemas`, and optional `jobs`.
- **Thin Controllers:** Route handlers are orchestration boundaries only. Business logic belongs in domain services.
- **Service Construction:** Services receive dependencies through `__init__`; never pull from a global locator.
- **Data Access:** Use SQLSpec via injected driver/session objects. Keep SQL and persistence logic in service/repository methods, not in controllers.
- **Async I/O:** Use `async/await` for all external I/O (database, network, AI clients).

## Dishka DI Standards
- **Centralized Wiring:** Configure Dishka once in app startup/factory (`setup_dishka(container, app)`), not per-route.
- **Plugin Integration:** Use `DomainPlugin(..., use_dishka_router=True)` so discovered controllers are Dishka-aware.
- **Route Signatures:** Prefer `Inject[T]` parameters in handlers. Do not use route-level `@inject` decorators when DishkaRouter is configured.
- **Provider Scopes:** Use `AppScope` for long-lived singletons (settings, shared clients) and `RequestScope` for request/session-scoped dependencies.
- **Domain Providers:** Each domain should expose explicit providers for its services and adapters, with clear dependency boundaries.
- **Tool/Job Context:** For background jobs and ADK tools, use `worker_scope`, `job_inject`, and `request_container_var` context patterns from `app/lib/di.py`.

## UI/UX Standards
- **Clean Aesthetics:** Use Tailwind CSS for a modern, clean, and polished aesthetic.
- **Performance:** Aim for low latency; use Oracle-backed caching for embeddings and responses.
- **Asset Pipeline:** Utilize Litestar-Vite for frontend bundling, type generation, and HMR.

## Quality Gates
- **Pre-merge Verification:** `uv run manage.py doctor` and `make test` must pass before closing implementation tasks.
- **Fail-Fast Tests:** Test commands must fail on pytest errors (no false-green targets).

## Agent System Standards
- **Cleanup Mandatory:** The Review Phase/Docs & Vision Agent MUST clean all `tmp/` directories and archive completed requirements to `.agent/archive/` (previously `specs/archive/`).
- **Research First:** Always check `.agent/knowledge/guides/` before executing external research.

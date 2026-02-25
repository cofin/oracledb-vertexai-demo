# Product Guidelines

## Core Mandates
- **Reference Standard:** Code must be a primary example of "how to do it right."
- **Simplicity:** Prefer readable, straightforward logic over complex abstractions.
- **Conciseness:** Avoid boilerplate and redundant code.
- **No Dead Code:** Unused imports, variables, and functions MUST be removed.
- **Correctness:** Full type hints and rigorous validation are required.

## Architectural Principles
- **Service Layer:** All business logic lives in `app/services/`.
- **Repository Pattern:** Database access is isolated in repositories using SQLSpec.
- **HTMX First:** Prioritize server-side interactivity with minimal client-side JavaScript.
- **Async Everywhere:** Use `async/await` for all I/O and non-blocking operations.

## UI/UX Standards
- **Clean Aesthetics:** Use Tailwind CSS for a modern, clean, and polished aesthetic.
- **Real-time Feedback:** Use HTMX for interactive elements like chat and search.
- **Performance:** Aim for low latency; use Oracle-backed caching for embeddings and responses.
- **Asset Pipeline:** Utilize **Litestar-Vite** for modern frontend bundling and HMR.

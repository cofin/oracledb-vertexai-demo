# Knowledge Base Index

This index lists the active, component-based guides for Cymbal Coffee. These guides synthesize the current authoritative state of the codebase.

## Component Guides

| Component / Category | Path | Purpose |
| --- | --- | --- |
| **System Architecture** | [guides/architecture.md](guides/architecture.md) | High-level system architecture, directory layouts, and dependency injection boundaries. |
| **Oracle Database & SQLSpec** | [guides/oracle-database.md](guides/oracle-database.md) | SQLSpec configurations, named SQL query patterns, vector storage, HNSW indexing, and container lifecycle. |
| **ADK Chat Agent Patterns** | [guides/adk-agent-patterns.md](guides/adk-agent-patterns.md) | ADK 2.0 workflow structures, intent routing, structured RAG grounding, chat streaming, caching, and telemetry. |
| **Store, Inventory & Maps** | [guides/store-inventory-maps.md](guides/store-inventory-maps.md) | Store hours, nearest-store location (Haversine), stock availability, browser coordinates privacy, and Google Maps integrations. |
| **Frontend & UI Development** | [guides/frontend-ui.md](guides/frontend-ui.md) | Jinja templating, HTMX events and extension configurations, Tailwind CSS, client-only Vite widgets, and mobile design rules. |
| **Testing & Verification** | [guides/testing-verification.md](guides/testing-verification.md) | pytest AnyIO async tests, conftest setup, parallel safety rules, conftest mocking, and manual check templates. |
| **Operations & Packaging** | [guides/operations-packaging.md](guides/operations-packaging.md) | PyApp onefile Bundle-Patch-Compile pipelines, distroless Docker builds, Release CI matrices, and Sphinx docs settings. |
| **Application settings** | [guides/settings.md](guides/settings.md) | Dataclass settings structure, environment parsing precedence, and settings cleanliness guidelines. |

## Knowledge Flywheel
Durable lessons discovered during task execution must be synthesized directly into these guides. Do not write per-flow historical files or link to archived specs. Maintain the chapters to reflect the *current* state of the codebase.

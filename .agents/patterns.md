# Project Patterns

> Consolidated learnings and patterns from all flows.
> This file is the single source of truth for project conventions.

<!-- truth: start -->
## Code Conventions

- **Licensing & Copyright:** Use concise SPDX identifiers at the top of every source file.
  - **Python/Shell/SQL:** Use `# SPDX-FileCopyrightText: 2024 Google LLC` and `# SPDX-License-Identifier: Apache-2.0`.
  - **JS/TS:** Use `// SPDX-FileCopyrightText: 2024 Google LLC` and `// SPDX-License-Identifier: Apache-2.0`.
  - **Mandatory:** Full license blocks are deprecated in favor of SPDX identifiers. All new files MUST include these headers.
- Use `app/domain/chat/services/_adk/runner.py` as the canonical ADK runner location in DDD projects.
- Preserve ADK runner context fields (`intent_details`, `search_details`, `store_details`, `products_found`, `stores_found`) through controller response payloads and UI rendering.
- Keep migration README updated with concrete baseline tables and type usage after schema modernization.
- Beads is authoritative for task status; markdown artifacts should mirror Beads via sync after status changes.

## Architecture Patterns

- **Litestar App Composition:** Keep app setup thin. Compose routes, plugins, dependencies, and middleware strictly from domain modules. Use async I/O universally.
- **Dishka DI:** Prefer centralized Dishka setup (`setup_dishka`) with `DomainPlugin(use_dishka_router=True)` and handler-level `Inject[T]` over route-level `@inject`.
- Dishka router integration (`Inject[ADKRunner]` on handlers, no route decorators) keeps DI explicit and framework-native.
- **SQLSpec Data Access:**
  - Always use typed adapters and context managers (`async with config.create_driver() as db:`).
  - Use `schema_type` to map typed results instead of raw dictionaries.
  - Prefer the query builder (`sql.select().to_statement()`) or `SQLFileLoader` over raw string concatenation.

## Gotchas & Warnings

- `make test` used `.ONESHELL` without `set -e`, which allowed false-green runs when pytest failed; enforce fail-fast in the test target.
- Integration tests using SQLSpec Oracle pool under `pytest-anyio` + xdist can hit event-loop binding issues; reset/close `db.pool_instance` in function-scoped fixtures to avoid cross-loop pool reuse.
- Cache integration tests should use unique keys per test run to remain deterministic under parallel workers.
- Fixture load ordering should include `store` before dependent semantic tables to keep imports deterministic.
- Product reads should normalize Oracle boolean nullability (`NVL(in_stock, TRUE)`) for stable typed API responses.
- **`OracleAsyncConfig` keyword-arg rename (sqlspec ≥ 0.46):** the constructor accepts `connection_config=` (was `pool_config=`). The old name is silently absorbed by `**kwargs` — credentials never reach the pool and every CLI fails with `DPY-4001 "no credentials specified"`. Audit any new sqlspec adapter wiring for this when bumping sqlspec.
- **Oracle 23ai vector pool / HNSW INMEMORY indexes:** any `CREATE VECTOR INDEX … ORGANIZATION INMEMORY NEIGHBOR GRAPH` requires a non-zero `vector_memory_size` allocated *before* the DDL runs (`ORA-51962` otherwise). `vector_memory_size` is a STATIC parameter — the change is SPFILE-only and only takes effect after a restart. The dev container handles this in `tools/oracle/on_init/00_configure_vector_memory.sql`; for shared/Autonomous DBs use `tools/oracle/configure_vector_memory.sql` as SYSDBA.
- **Oracle Database Free Edition memory cap:** Free locks `sga_max_size` / `sga_target` (~1.5 GB SGA + 0.5 GB PGA = 2 GB hard ceiling) and rejects bumps with `ORA-56752`. The vector pool must therefore fit *inside* the existing SGA — 512 MB is the project default and gives ~25× headroom for the demo dataset (~1100 vectors at 3072 dims). Standard/Enterprise/Autonomous have no such cap.
- **`V$SGAINFO` row name for the vector pool:** the row is reported as `Vector Memory Area`, not `Vector Memory`. Verification SQL must match either label; the on_startup script in this repo does.
- **Embedding dim ↔ DDL coupling:** `VECTOR(N, FLOAT32)` columns and the embedding model output are co-versioned. When changing dims (e.g. `text-embedding-004` 768 → `gemini-embedding-001` 3072), modify the baseline DDL, set `output_dimensionality=N` on `EmbedContentConfig`, and regenerate fixtures — there is no implicit truncation/padding at the DB layer.
- **Stale fixture vectors against a new schema:** `FixtureProcessor(expected_vector_dim=N)` skips vector columns whose payload length differs from `N`, with a one-shot warning per column. This lets the existing `*.json.gz` fixtures load against an updated `VECTOR(N)` schema; `bulk-embed --include-exemplars` then fills in the new embeddings via Vertex AI.
- **`bulk-embed --include-exemplars`:** without it, intent classification can't run after a dim change because `intent_exemplar.embedding` ends up NULL post-load (its column is intentionally nullable so the load succeeds). `clear-cache --include-exemplars` is its destructive counterpart.

## Testing Patterns

- Maintain both lightweight chat UI and richer dashboard UI tests to keep quick-path and analytics-path regressions visible.
- UI verification is safer when tests assert rendered contextual fields (products/stores/results), not only final answer text.

## Context for AI Assistants

- Persona-aware system prompt composition (`BASE_SYSTEM_INSTRUCTION` + persona overlay) keeps one static ADK agent reusable while preserving behavioral flexibility.
- Preserve generated API/types artifacts and route scaffolding early (`litestar assets generate-types`) to reduce frontend/backend contract drift.
- Modern Oracle baseline is already captured in `0001_cymball_coffee_products.sql` with `BOOLEAN`, `JSON`, and `VECTOR` columns plus `store` table parity.
- Maintaining `.agents/knowledge/index.md` as a compact registry makes cross-flow recall faster than searching raw specs.
- During migration from legacy guides, preserving concise gotchas in `patterns.md` yields better downstream implementation quality.
<!-- truth: end -->

---
type: Log
title: Project Log
description: Historical change log and completed milestone record for Cymbal Coffee
---

# Project Log

Historical change log and completed milestone record for Cymbal Coffee.

## 2026-10-15: Explore Hybrid RRF Telemetry, Validated Vector/FTS Calculator & 34-Slide DBA Deck Finalization
- `explore-hybrid-rrf-and-calculator` (`eeef458`, `a223104`): Upgraded the `/explore` page and `OracleVectorSearchService` to run single-query Oracle 26ai Hybrid RRF (`hybrid-search-products` / `hybrid-search-products-by-store` with `prod_vec_top` subquery isolation so `ROWNUM AS vector_rank` preserves `VECTOR INDEX HNSW SCAN IN-FILTER` alongside `DOMAIN INDEX`), surfaced per-row RRF score, vector rank, lexical rank, and `DBMS_XPLAN` access-path badges in the UI, and calibrated `src/resources/vector-calculator.js` against Oracle 26ai `DBMS_VECTOR.INDEX_VECTOR_MEMORY_ADVISOR` (`1.25x` raw vector bytes + `~640 B/row` graph links for HNSW; `1.1x` disk partitions + `~sqrt(N)` SGA centroids for IVF) and `CTXSYS.CONTEXT` (`DR$<idx>$I`/`$X`/`$K`/`$R` ~35% text volume).
- `oracle-gemini-2026-dba-deck` (`37dc6a1`): Finalized the 34-slide DBA-first storyboard (`.agents/bundles/knowledge/presentation/{storyboard,speaker-guide,verified-facts}.md`), extended `tools/slides/highlight.py` with YAML and SQLcl/bash syntax highlighting, synthesized Exadata AI Smart Scan and `sql -mcp` (`DBTOOLS$MCP_LOG`) research into `verified-facts.md` and `patterns/operations.md`, and normalized all Flow v2 spec/task frontmatter under `.agents/bundles/specs/`.

## 2026-10-13: "Oracle in the Age of Gemini" Deck Archive & Full-Codebase Review Hardening
- `oracle-gemini-2026-deck`: Completed and archived the 36-slide DBA presentation plus 17 backup slides, offline Google Slides CLI (`tools/slides/{cli,deck,diff,highlight,qr,validate}.py`), dark-slide palette detection (`#212226` on slides 17, 18, and 22), and verified Oracle 26ai `DBMS_VECTOR.UTL_TO_EMBEDDING` / Select AI documentation and live container checks in `.agents/bundles/knowledge/presentation/`.
- `full-codebase-review-remediation`: Executed multi-skill review across Python backend, Litestar, Oracle 26ai/SQLSpec, AI Runtime/MCP/A2A, Web/HTMX, Slides, Docs, and OKF v0.2 bundles; rewrote `vector-search-products-by-store` to use an HNSW `candidate_products` CTE (`FETCH APPROX FIRST 50 ROWS ONLY`), added defensive Oracle Text brace-escaping in `ProductService.search_hybrid`, isolated `response_cache` from multi-turn session history, validated `Tool.invoke` arguments and `get_display_history` ownership, hardened `Settings.configure_genai_env()` against placeholder project IDs, and expanded `check_code_hygiene.py`, `test_test_suite_guards.py`, and `test_okf_layout.py`.

## 2026-10-13: Hybrid RRF Search, Oracle Queues, Static Gate Hardening & OKF v0.2 Restructuring
- `coffee-agent-stabilization-and-hybrid-search`: Completed single-query Oracle 26ai Hybrid RRF (`hybrid-search-turn` at $k=60$ with `MULTI_COLUMN_DATASTORE` `CONTAINS`/`SCORE(1)` + HNSW `VECTOR_DISTANCE ... FETCH APPROX`) and `hybrid-term-hits` (`JSON_TABLE` + `CONTAINS`) for off-menu brand detection.
- `oracle-queues`: Integrated `litestar-queues[sqlspec]` on Oracle 26ai (`FOR UPDATE SKIP LOCKED`) with a dedicated LOB-isolated `DatabaseSettings.get_queue_config()` pool (`session_key="queue_db_session"`), `@task("products.embed_missing")`, `@task("system.cache_cleanup")`, and `coffee worker run/status`.
- `platform-alignment`: Modularized settings (`src/app/lib/settings/`) and Dishka providers (`src/app/ioc/`), squashed baseline DDL into `0001_cymball_coffee_products.sql`, separated `sql_loader` (`src/app/lib/sql.py`) from `app.config`, and split Vertex AI `LOCATION` (`us-central1` embeddings) from `CHAT_LOCATION` (`global` for `gemini-3.8-flash`).
- `test-and-ci-hardening`: Flattened `src/tests/{unit,integration}/`, added AST/tokenize meta-guards (`test_test_suite_guards.py`, `test_okf_layout.py`), added `tools/ci/check_code_hygiene.py` and `tools/ci/check_litestar_security.py`, and configured root `AGENTIC_REVIEW` with 4 domain review skills under `.agents/skills/review-*`.
- `okf-knowledge-restructuring`: Reorganized `.agents/bundles/knowledge/` into `architecture/`, `domains/`, `testing/`, `patterns/`, and `gotchas/`, and contracted completed stabilization specs.

## 2026-10-08: Native Agentic Runtime (Gemini 3.8 Flash, A2A & MCP)
- `native-agentic-runtime`: Decommissioned Google ADK and migrated conversational workflows to native dynamic agentic intelligence platform in `src/app/domain/ai/`.
- Runtime Primitives: High-performance `msgspec.Struct` contracts (`Content`, `Part`, `FunctionCall`, `FunctionResponse`, `AgentEvent`, `Usage`), Gemini schema converter, and type-safe `declare()` tool wrapper with `execute_parallel()`.
- Model Acceleration: `GeminiModelClient` targeting `gemini-3.8-flash` with native thought suppression, exponential backoff retries, and token accounting.
- Persistence: `OracleSessionStore` and `OracleEventStore` utilizing named SQL in `src/app/db/sql/ai-runtime.sql` (`AGENT_SESSION`, `AGENT_EVENT`) with ACID transaction guarantees.
- Streaming: Re-entrant `AgentRuntime.execute_turn()` with turn/step limits and `AgentStreamService` SSE adapter emitting keep-alive pings (`type: ping`), tool lifecycle events, text deltas, and usage summaries.
- Multi-Protocol: Stateless `LitestarMCP` (`POST /mcp`) with route-annotated tools (`mcp_tool="search_coffee_products"`) and `LitestarA2A` (`POST /a2a`, `GET /.well-known/agent-card.json`) with `CoffeeAgentExecutor`.
- Hardened Security & Telemetry: `litestar-security` integration with `SecurityHeadersConfig.hardened()` and `PublicController` subclassing; `OpenTelemetryPlugin` enabled by default with SQLSpec database spans.

## 2026-10-07: Flow Setup & OKF v0.2 Migration
- Transitioned framework from legacy tracker to OKF v0.2 knowledge bundles under `.agents/bundles/`.
- Scaffolding: `product/`, `knowledge/`, `specs/`, `research/`, `log.md`, `index.md`.
- Consolidated legacy `flows.md` and archived milestones into `log.md`.
- Synthesized `knowledge/workflow.md` from canonical template with project-native commands (`make test`, `make lint`, `make typecheck`).
- Partitioned legacy `patterns.md` into evidence-backed chapters under `knowledge/patterns/` (`architecture.md`, `code-style.md`, `testing.md`, `operations.md`).

## 2026-06-26: Explore Search UX Fixes
- `fix-explore-search-ux`: Resolved explore page search usability issues by aligning query parameter to `query` and handling form submission in HTMX.

## 2026-06-24: Cloud Run & ORDS Deployment Labs
- `cloudrun-gce-lab`: Shipped Cloud Run app readiness, GCE Oracle DB appliance, Cloud Build + Cloud Run deploy pipeline, renamed current lab to GCE-only, and authored new Cloud Run lab module with verification.
- `cloudrun-ords-deploy`: Deployed ORDS to Cloud Run stateless, peered via Direct VPC, utilizing Secret Manager for system password, enabling REST APIs against private GCE database VM.
- `adk2-sqlspec-migration`: Integrated SQLSpec ADK 2.0 store contract (singular table names, `append_event` history) and updated default model to `gemini-3.1-flash-lite`.

## 2026-06-23: Oracle APEX Integration & Lab Hardening
- `oracle-apex-integration`: Implemented APEX media staging, idempotent install/upgrade engine + `infra apex` CLI, ORDS sidecar, and APEXlang source for operations console.
- `oracle-schema-annotations`: Verified 26ai schema annotations using `USER_ANNOTATIONS_USAGE`.
- `inventory`: Seeded store inventory data, deterministic availability routing, inventory-aware vector search (RAG), live HTMX inventory UI, and coordinate/privacy guidance.
- `demo-simplification`: Consolidated settings, streamlined AI chat to SSE streaming, improved ADK readability, added Maps directions, split frontend modules, and simplified test suites.

## 2026-05-02: PyApp Packaging & Reset Milestones
- `pyapp-packaging_20260429`: Shipped Bundle-Patch-Compile path, cargo-zigbuild GLIBC 2.17 launchers, distroless Dockerfile, and dual-architecture GitHub Releases matrix.
- `store-location-inventory-chat_20260501`: Store coordinates, Haversine nearest-store queries, stock availability routing, browser location opt-in, and no-key Google Maps URLs.
- `cymbal-coffee-reset_20260429`: Foundation bump, domain service restructure, ADK 2 runner, HTMX + Vite frontend, vector calculator, and test reorganization.

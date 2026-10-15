---
type: Guide
title: Technology Stack
description: Tech stack components for Litestar, Oracle 26ai, Vertex AI, Native AgentRuntime, MCP/A2A, and litestar-queues
tags:
  - architecture
  - tech-stack
---

# Technology Stack

<!-- truth: start -->
## Backend
- **Language:** Python 3.12+ (managed via `uv`)
- **Framework:** Litestar 2 (`litestar-autowire`, `litestar-security`, `litestar-htmx`, `litestar-vite`)
- **Server:** Granian (wired via `litestar-granian`)
- **Dependency Injection:** Dishka (`src/app/ioc/`)
- **AI & Protocols:** Google Vertex AI (`google-genai>=1.68.0`, `gemini-3.8-flash`, `gemini-embedding-2`), native `app.domain.ai` `AgentRuntime`, `litestar-mcp[a2a,google-genai,opentelemetry]>=0.15.0`
- **Background Queues:** `litestar-queues[sqlspec]>=0.12.0` on Oracle 26ai

## Frontend
- **Framework:** HTMX 2.x + Jinja2 templates (no React/SPA)
- **Asset Pipeline:** Vite (wired via `litestar-vite`)
- **Styling:** Tailwind CSS v4
- **Charts:** ApexCharts

## Persistence
- **Database:** Oracle AI Database 26ai (`VECTOR(3072, FLOAT32)`, HNSW `INMEMORY NEIGHBOR GRAPH`, `CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE`)
- **Data Access:** SQLSpec (with `python-oracledb` and `mypyc`)
- **Browser Sessions:** Server-side sessions in Oracle (`app_session`)
- **Agent Sessions:** Native SQLSpec `OracleSessionStore` (`agent_session`) and `OracleEventStore` (`agent_event`)
- **Queue Persistence:** `OracledbAsyncQueueStore` with a dedicated LOB-isolated `DatabaseSettings.get_queue_config()` pool

## Tooling
- **Package Managers:** `uv` (Python), `npm` (JS)
- **VCS Hook Runner:** `prek`
- **Lint/Format:** Ruff, Mypy, Pyright, TypeScript compiler check, Sphinx (`sphinx-build -W`)
<!-- truth: end -->

For detailed component mappings, see [architecture/system-architecture.md](../knowledge/architecture/system-architecture.md).

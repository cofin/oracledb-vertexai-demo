---
type: Guide
title: Core Platform (`lib/`, `ioc/`, `server/`, `cli/`)
description: Modular settings, SQLSpec loader, Dishka providers, Litestar plugin wiring, and coffee CLI
tags:
  - settings
  - dishka
  - server
  - cli
  - queues
---

# Core Platform (`lib/`, `ioc/`, `server/`, `cli/`)

## 1. Modular Settings (`src/app/lib/settings/`)

Settings are organized into focused modules under `src/app/lib/settings/`:
- `_env.py`: Environment parsing helpers (`get_env`, `.env` fallback loading).
- `_app.py`: `AppSettings` (name, debug, secret key, CORS, optional `MCP_API_KEY`).
- `_server.py`: `ServerSettings` and `ViteSettings` (`ViteConfig(types=False)` pointing at `src/resources/`).
- `_database.py`: `DatabaseSettings` (`get_config()` for primary `OracleAsyncConfig` and `get_queue_config()` with `session_key="queue_db_session"` for LOB-isolated `litestar-queues` polling).
- `_ai.py`: `AISettings` (`PROJECT_ID`, `LOCATION`, `CHAT_LOCATION="global"`, `DEFAULT_CHAT_MODEL="gemini-3.8-flash"`, `DEFAULT_EMBEDDING_MODEL="gemini-embedding-2"`, `EMBEDDING_DIMENSIONS=3072`) and `ChatSettings`.
- `_log.py` & `_otel.py`: `LogSettings` and `OpenTelemetrySettings`.
- `_maps.py`: `MapsSettings` (`ENABLE_EMBED`, `EMBED_API_KEY`).
- `_queue.py`: `QueueSettings` (`ENABLED`, `BACKEND`, `EXECUTION_BACKEND`, `WAKEUP_MODE`, `CONCURRENCY`, `POLL_INTERVAL`).

Always retrieve settings via `Settings.from_env()` (cached via `@lru_cache(maxsize=1)`).

## 2. Shared Infrastructure (`src/app/lib/`)

- `di.py`: Exports `Inject = FromDishka` for Litestar controller handler parameters.
- `sql.py`: Exports `sql_loader` (`SQLFileLoader` loading `src/app/db/sql/*.sql`) without importing `app.config`.
- `service.py`: `SQLSpecAsyncService` and `OracleAsyncService` base classes wrapping `OracleAsyncDriver`.
- `schema.py`: `BaseStruct` (`msgspec.Struct` base class) and `CamelizedBaseStruct` (`rename="camel"`).
- `jobs.py`: `create_task_container()` context manager providing an isolated Dishka container for background `litestar-queues` jobs.

## 3. Dishka Providers (`src/app/ioc/`)

- `_database.py` (`ConfigProvider`, `DBProvider`), `_ai.py` (`AIProvider`), and `_domain.py` (`DomainServiceProvider`) wire `Scope.APP` and `Scope.REQUEST` dependencies.
- Never add `from __future__ import annotations` to `src/app/ioc/*.py`.

## 4. Server & CLI (`src/app/server/` & `src/app/cli/`)

- `src/app/server/core.py` and `src/app/server/plugins.py` configure `SecurityPlugin`, `SQLSpecPlugin`, `VitePlugin`, `GranianPlugin`, `HTMXPlugin`, `LitestarMCP`, `LitestarA2A`, `QueuePlugin`, `AutowirePlugin`, and Dishka integration.
- `src/app/cli/main.py` and `src/app/cli/commands.py` expose end-user lifecycle commands on `uv run coffee`: `run` (including `--no-worker`), `upgrade`, `load-fixtures`, `export-fixtures`, `bulk-embed`, `clear-cache`, `model-info`, `worker run`, `worker status`, and `queues`.

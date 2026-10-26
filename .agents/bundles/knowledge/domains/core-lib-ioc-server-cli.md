---
type: Guide
title: Core Platform (`lib/`, `ioc/`, `server/`, `cli/`)
description: Modular settings, SQLSpec 0.69.0 service and loader primitives, Dishka providers, Litestar plugin wiring, coffee CLI, and local Oracle/demo tooling
tags:
  - settings
  - dishka
  - server
  - cli
  - queues
  - sqlspec
---

# Core Platform (`lib/`, `ioc/`, `server/`, `cli/`)

## 1. Modular Settings (`src/app/lib/settings/`)

Settings live in focused dataclass modules under `src/app/lib/settings/` and are accessed through `Settings.from_env()` (cached via `@lru_cache(maxsize=1, typed=True)`):
- `_env.py`: Environment parsing helpers (`BASE_DIR`, `DEFAULT_MODULE_NAME`, `_env_bool`, `_env_int`, `_env_float`, `_env_str`, `_env_cors`).
- `_app.py`: `AppSettings` (`DEBUG`, `SECRET_KEY`, `NAME`, `URL`, `ALLOWED_CORS_ORIGINS`, CSRF settings, optional `MCP_API_KEY` for `/mcp` and `/a2a`, and optional `APEX_GATEWAY_API_KEY` for `/api/apex/ai/v1/*`).
- `_server.py`: `ServerSettings` (`HOST`, `PORT`, `RELOAD`, `WORKERS`) and `ViteSettings` (`ViteConfig(mode="htmx", types=False)` pointing at `src/resources/`).
- `_database.py`: `DatabaseSettings` (`create_config()` / `get_config()` for primary SQLSpec `0.69.0` `OracleAsyncConfig` using default `fetch_lobs=False` inline `str` / `bytes` reads for CLOB/BLOB < 1 GB, `driver_features={"enable_session_tracing": True}`, wire-level `sqlcommenter` (`enable_sqlcommenter=True`, `sqlcommenter_enable_context=True`, `sqlcommenter_enable_traceparent=True`), `ObservabilityConfig`, and Autonomous `wallet_zip` extraction via `extract_oracle_wallet_zip` / `parse_tnsnames_ora`; plus `get_queue_config()` with `min=1, max=4`, `session_key="queue_db_session"`, and `"manage_lifespan": True` for isolated `litestar-queues` polling).
- `_ai.py`: `AISettings` (`project_id`, `location="global"`, `gcp_region="us-central1"`, `api_key`, `chat_model="gemini-3.8-flash"`, `intent_model_override`, `embedding_model="gemini-embedding-2"`, `embedding_dimensions=3072`), `PLACEHOLDER_VALUES`, and `ChatSettings`.
- `_log.py` & `_otel.py`: `LogSettings` and `OpenTelemetrySettings`.
- `_maps.py`: `MapsSettings` (`ENABLE_EMBED`, `EMBED_API_KEY`, `embed_enabled`).
- `_queue.py`: `QueueSettings` (`ENABLED`, `IN_MEMORY`, `BACKEND`, `EXECUTION_BACKEND`, `WAKEUP_MODE`, `CONCURRENCY`, `POLL_INTERVAL`, `MANAGE_SCHEMA`).

## 2. Shared Infrastructure (`src/app/lib/` & `src/app/utils/`)

- `src/app/lib/di.py`: Exports `Inject` (`FromDishka`), `LitestarProvider`, `LitestarRouter`, `setup_dishka`, `request_container_var`, and `worker_container_var`.
- `src/app/lib/service.py`: Exports `default_sql_loader()` (`@lru_cache(maxsize=1)` loading `src/app/db/sql/*.sql` without importing `app.config`), `OracleAsyncService(SQLSpecAsyncService[OracleAsyncDriver])`, `OracleLoaderService(OracleAsyncService)` (`self.get_sql(name)`), `FilterTypes`, `OffsetPagination`, and `create_filter_dependencies`.
- `src/app/lib/schema.py`: Exports `FrozenBaseStruct(msgspec.Struct, frozen=True, gc=False, omit_defaults=True)`, `CamelizedFrozenStruct(FrozenBaseStruct, rename="camel", frozen=True, gc=False, omit_defaults=True)`, and `Message`.
- `src/app/lib/text_search.py`: Exports `ORACLE_TEXT_RESERVED_WORDS`, `ORACLE_TEXT_STOPWORDS`, `extract_search_tokens`, `build_oracle_text_query`, and `build_oracle_proximity_query`.
- `src/app/lib/jobs.py`: Exports `task_container_scope()` and `get_task_container()` providing an isolated `Scope.REQUEST` Dishka child container for background `litestar-queues` jobs.
- `src/app/lib/security.py` & `src/app/lib/exceptions.py`: `build_security_config(settings)` (`secrets.compare_digest` verification for `MCP_API_KEY`), `ApplicationError`, `AIServiceUnconfigured`, `ai_service_unconfigured_handler`, `is_credential_error`, and `is_expected_service_unavailable`.
- `src/app/lib/log/`: Structured `structlog` processors, Cloud Logging attribute mapping, and `StructlogMiddleware`.
- `src/app/utils/serialization.py`: Centralized `msgspec.json` and Oracle `Decimal` / NumPy helpers (`encode_json`, `encode_json_bytes`, `format_json`, `decode_json`, `to_schema`, `schema_dump`, `sanitize_for_json`).

## 3. Dishka Providers (`src/app/ioc/`)

- `src/app/ioc/__init__.py` exports `PROVIDERS = (ConfigProvider, DBProvider, AIProvider, DomainServiceProvider)`, `get_providers(...)`, and `create_container(...)` across `_config.py`, `_database.py`, `_ai.py`, and `_domain.py`.
- Never add `from __future__ import annotations` to `src/app/ioc/` provider modules; Dishka inspects return and parameter annotations at runtime.

## 4. Server, CLI & Developer Tooling (`src/app/server/`, `src/app/cli/`, `tools/`)

- `src/app/server/asgi.py`, `src/app/server/core.py` (`ApplicationCore`), `src/app/server/plugins.py`, and `src/app/server/mcp/_config.py` wire `SecurityPlugin`, `SQLSpecPlugin`, `VitePlugin`, `GranianPlugin`, `HTMXPlugin`, `LitestarMCP`, `LitestarA2A`, `QueuePlugin`, `AutowirePlugin`, and Dishka integration.
- `src/app/cli/main.py`, `src/app/cli/commands.py`, and `src/app/cli/_helpers/` (`fixtures.py`, `ords.py`) expose lifecycle commands on `uv run coffee`: `run` (including `--no-worker` and Cloud Run `PORT` fallback), `upgrade`, `load-fixtures`, `export-fixtures`, `bulk-embed`, `clear-cache`, `model-info`, `configure-apex-cdn` (executes packaged `src/app/db/sql/deploy/configure-apex-cdn.sql`, paired with `src/app/db/sql/deploy/revert-apex-cdn.sql`), `worker` (`run`, `status`, `run-task`, `run-maintenance`), and `queues`.
- `tools/oracle/` (`adb.py`, `database.py`, `wallet.py`, `apex_lang.py`, `apex_catalog.py`, `apex_vertex.py`) and `tools/demos/` (`cli.py`, `shell.py`, `web.py`) drive local ADB-Free 26ai + APEX 26.1 orchestration (`manage.py infra`) and deterministic `vhs` / Playwright demo recordings (`manage.py demos`).

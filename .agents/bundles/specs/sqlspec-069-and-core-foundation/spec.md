---
type: Spec
flow_id: sqlspec-069-and-core-foundation
title: SQLSpec 0.69.0 Adoption, Frozen Wire Structs, OracleLoaderService, and Decoupled Dishka IoC
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-10-24T19:26:00Z
updated_at: 2026-10-24T19:26:00Z
description: First stacked PR upgrading to SQLSpec 0.69.0 (enable_session_tracing, wire-level sqlcommenter, queue_db manage_lifespan, native wallet_zip), adding FrozenBaseStruct/CamelizedFrozenStruct, centralized msgspec serialization, app.lib.exceptions, and OracleLoaderService, decoupling app.config and app.ioc from app.server, and tightening nested-import CI gates.
tags:
  - refactor
  - sqlspec
  - settings
  - ioc
  - architecture
parent_prd: platform-alignment-apex-vertex-prd
research: []
---

# Flow: SQLSpec `0.69.0` Adoption, Frozen Wire Structs, `OracleLoaderService`, and Decoupled Dishka IoC

**Flow ID:** `sqlspec-069-and-core-foundation`
**Parent PRD:** [`platform-alignment-apex-vertex-prd`](../platform-alignment-apex-vertex-prd/spec.md)
**Depends On:** None (PR 1 of 5 in stack — targets `main`)
**Proposed Branch & PR Title:** `refactor/sqlspec-069-core` — `refactor(core): adopt sqlspec 0.69.0 tracing, wallet config, and loader services`

---

## Specification

### Code Analysis Summary

Files examined:

- `pyproject.toml:21` — Pins `sqlspec[litestar,mypyc,oracledb,performance]>=0.65.0` and omits an explicit `msgspec` floor.
- `src/app/lib/settings/_database.py:52-60,118-215` — Retains dead `ADK_IN_MEMORY` / `ADK_ENABLE_MEMORY` / `ORACLE_ADK_IN_MEMORY` fields; `create_config` passes `driver_features={"enable_AutoLob": True}` at line 125 (rejected by SQLSpec `0.69.0` `VALID_ORACLE_DRIVER_FEATURE_KEYS`), `get_queue_config` (lines 149-168) omits `"manage_lifespan": True`, and `_build_pool_config` (lines 174-200) manually mutates `os.environ["TNS_ADMIN"]` and disables TLS hostname checks (`ssl_ctx.check_hostname = False`) instead of using SQLSpec `0.69.0`'s `wallet_zip`.
- `src/app/lib/settings/{__init__,_ai,_app,_database,_env,_log,_maps,_otel,_queue,_server}.py` — All 11 `@dataclass(frozen=True)` settings classes (`Settings`, `AppSettings`, `ServerSettings`, `ViteSettings`, `LogSettings`, `DatabaseSettings`, `AISettings`, `ChatSettings`, `MapsSettings`, `OpenTelemetrySettings`, `QueueSettings`) omit `slots=True`; `_queue.py` defines 8 duplicate lowercase alias properties mirroring uppercase fields.
- `src/app/lib/schema.py:1-16` & `src/app/utils/serialization.py:1-60` — `BaseStruct` omits `frozen=True, gc=False`; `serialization.py` lacks `encode_json_bytes`, `format_json`, `decode_json`, and `to_schema` helpers.
- `src/app/lib/service.py:1-41` — `OracleAsyncService` only accepts a live `OracleAsyncDriver` session and does not encapsulate `SQLFileLoader` or app-scoped `OracleAsyncConfig` sessions.
- `src/app/lib/log/_security.py:1-54`, `src/app/lib/log/_middleware.py:1-125`, `src/app/lib/log/_filters.py:1-58`, `src/app/config.py:1-305`, `src/app/server/core.py:35-50`, `src/app/server/plugins.py:1-169` — `_security.py` (`apply_security_headers`, `build_security_headers`) duplicates `SecurityPlugin` in `src/app/lib/security.py` while `BeforeSendHandler` in `_middleware.py` handles structured HTTP request/response logging; `SuppressADKWarningsFilter` and `google.adk` warning suppressions remain from the retired ADK stack; `config.py` and `plugins.py` use function-scoped imports that require exceptions in `tools/ci/check_code_hygiene.py:34-41` and `src/tests/unit/test_test_suite_guards.py:72-80`.
- `src/app/ioc/__init__.py:1-41`, `_config.py:1-66`, `_database.py:1-55`, `_ai.py:1-192`, `_domain.py:1-108` — Providers import `app.config` and `app.server.plugins` directly, keep `AgentStreamService` at `Scope.REQUEST` instead of `Scope.APP`, and retain compatibility aliases (`LitestarPersistenceProvider`, `IntegrationsProvider`, `make_container`).

### Relevant Patterns

- [Core Platform (`lib/`, `ioc/`, `server/`, `cli/`)](../../knowledge/domains/core-lib-ioc-server-cli.md) — `Settings.from_env()` boundary, zero `from __future__ import annotations` in `src/app/ioc/`, separate `queue_db_session` pool.
- [Oracle 26ai, SQLSpec & Queues Gotchas](../../knowledge/gotchas/oracle-sqlspec-and-queues.md) — Queue pool LOB isolation (`OracledbAsyncQueueStore` sets `fetch_lobs=False`).
- [Testing Rulebook](../../../../src/tests/AGENTS.md) — 5-section test module layout, docstrings on every test function, zero inline `#` comments, preserve `KEEP_LIST_PATHS`.

### Requirements

- **PLAT-REQ-01 (SQLSpec `0.69.0` Floor, Tracing, `wallet_zip` & Slotted Settings)**:
  - Bump `sqlspec[litestar,mypyc,opentelemetry,oracledb,performance]>=0.69.0` and `msgspec>=0.22.0` in `pyproject.toml`, and update `.gitignore` `node_modules` entries to match worktree symlinks cleanly.
  - In `DatabaseSettings` (`src/app/lib/settings/_database.py`), replace `driver_features={"enable_AutoLob": True}` with `driver_features={"enable_session_tracing": True}` and wire-level `statement_config=default_statement_config.replace(enable_sqlcommenter=True, sqlcommenter_enable_context=True, sqlcommenter_enable_traceparent=True)` (from `sqlspec.adapters.oracledb.core`), add `"manage_lifespan": True` on `get_queue_config()`, and pass `"wallet_zip": str(Path(self.WALLET_LOCATION).resolve())` + `"wallet_password"` in `_build_pool_config` without `os.environ["TNS_ADMIN"]` mutation or `check_hostname = False`.
  - Add `slots=True` across all 11 settings dataclasses (`src/app/lib/settings/*.py`), remove dead `ADK_IN_MEMORY` / `ADK_ENABLE_MEMORY` / `ORACLE_ADK_IN_MEMORY` fields from `DatabaseSettings` and obsolete ADK comments from `tools/scripts/setup-env.sh`, and remove the 8 duplicate lowercase alias properties on `QueueSettings`.
- **PLAT-REQ-02 (`FrozenBaseStruct`, Centralized Serialization, `app.lib.exceptions`, Frozen Security & `OracleLoaderService`)**:
  - Add `FrozenBaseStruct(msgspec.Struct, frozen=True, gc=False, omit_defaults=True)`, `CamelizedFrozenStruct(FrozenBaseStruct, rename="camel")`, and `Message` in `src/app/lib/schema.py` (retaining `BaseStruct` and `CamelizedBaseStruct` until PR 2 migrates domain schemas).
  - Add `encode_json_bytes`, `format_json`, `decode_json`, and `to_schema` in `src/app/utils/serialization.py`.
  - Create `src/app/lib/exceptions.py` defining `ApplicationError`, `AIServiceUnconfigured(ServiceUnavailableException, ApplicationError)`, `ai_service_unconfigured_handler`, `is_credential_error`, and `is_expected_service_unavailable`, and re-export `AIServiceUnconfigured` in `src/app/domain/chat/exceptions.py` until PR 2 deletes it.
  - Freeze `@dataclass(frozen=True, slots=True)` principal/context value objects in `src/app/lib/security.py`.
  - Extend `src/app/lib/service.py` with `__slots__ = ()`, dual `driver_or_config: OracleAsyncDriver | OracleAsyncConfig` support (`provide_app_session()`), `default_sql_loader()` (`SQLFileLoader` loading `BASE_DIR / "db" / "sql"`), and `OracleLoaderService(OracleAsyncService)` exposing `self.get_sql(name)`.
- **PLAT-REQ-03 (Logging Cleanup, `config.py` Reset Hooks & Nested-Import Gate Tightening)**:
  - Delete `src/app/lib/log/_security.py` (`apply_security_headers`, `build_security_headers`), keep `BeforeSendHandler` in `src/app/lib/log/_middleware.py` solely for structured HTTP request/response logging (`SecurityPlugin` in `src/app/lib/security.py` owns security headers), and remove `SuppressADKWarningsFilter` and `google.adk` warning suppressions from `src/app/lib/log/_filters.py` and `src/app/config.py`.
  - Move all function-scoped imports in `src/app/config.py` and `src/app/server/plugins.py` to module top-level, decouple `setup_logging()` from `config._initialize()`, add `register_reset_hook` in `src/app/config.py`, and tighten `ALLOWED_LAZY_IMPORT_FILES` in `tools/ci/check_code_hygiene.py` and `ALLOW_NESTED_IMPORTS` in `src/tests/unit/test_test_suite_guards.py` strictly to `src/app/cli/{commands,main}.py`.
- **PLAT-REQ-04 (Decoupled Dishka IoC & Composition-Root Container Factory)**:
  - Remove `app.config` and `app.server` imports from `src/app/ioc/{_database,_ai,_domain}.py`; provide `SQLFileLoader`, `ChatSettings`, and `QueueSettings` from `ConfigProvider`, allow optional composition-root `db_config`/`queue_config`/`queue_service` on `DBProvider`, move `AgentStreamService` to `Scope.APP` on `AIProvider`, type Vertex credentials with `CredentialProtocol`, and remove `LitestarPersistenceProvider`, `IntegrationsProvider`, and `make_container` from `src/app/ioc/__init__.py` (updating `asgi.py`, `cli/main.py`, `cli/utils.py`, and `lib/jobs.py` to call `create_container(...)`).

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `PLAT-REQ-01` | `1.1` | `behavior_tdd` | `pyproject.toml`, `src/app/lib/settings/*.py`, `tools/scripts/setup-env.sh` | `src/tests/unit/lib/test_settings.py`, `src/tests/unit/lib/test_queue_settings.py` |
| `PLAT-REQ-02` | `1.2` | `behavior_tdd` | `src/app/lib/schema.py`, `src/app/utils/serialization.py`, `src/app/lib/exceptions.py`, `src/app/lib/service.py`, `src/app/lib/security.py` | `src/tests/unit/lib/test_service_and_serialization.py`, `src/tests/unit/server/test_security_and_mcp.py` |
| `PLAT-REQ-03` | `1.3` | `characterization` | `src/app/lib/log/_security.py`, `src/app/lib/log/__init__.py`, `src/app/lib/log/_filters.py`, `src/app/config.py`, `src/app/server/core.py`, `src/app/server/plugins.py`, `tools/ci/check_code_hygiene.py` | `src/tests/unit/lib/test_log.py`, `src/tests/unit/test_test_suite_guards.py` |
| `PLAT-REQ-04` | `1.4` | `behavior_tdd` | `src/app/ioc/__init__.py`, `src/app/ioc/_config.py`, `src/app/ioc/_database.py`, `src/app/ioc/_ai.py`, `src/app/ioc/_domain.py`, `src/app/server/asgi.py`, `src/app/cli/main.py`, `src/app/cli/utils.py`, `src/app/lib/jobs.py` | `src/tests/unit/ioc/test_ioc_and_services.py`, `src/tests/unit/ioc/test_ioc_integrations.py`, `src/tests/unit/domain/chat/test_exceptions.py` |

---

## Implementation Plan

### Phase 1: SQLSpec `0.69.0` Settings, Schemas, Loader Services & Decoupled IoC

- [ ] 1.1 Upgrade `pyproject.toml` to SQLSpec `0.69.0`, adopt `enable_session_tracing` + wire `sqlcommenter` + `wallet_zip` + `queue_db` `manage_lifespan`, and slot/clean all settings dataclasses
- [ ] 1.2 Add `FrozenBaseStruct`, centralized `msgspec` serialization helpers, `app.lib.exceptions`, frozen `security.py` dataclasses, and `OracleLoaderService`
- [ ] 1.3 Delete `log/_security.py` and ADK log filters, decouple `app.config` via `register_reset_hook` and top-level imports, and tighten nested-import CI gates
- [ ] 1.4 Decouple `src/app/ioc/` from `app.config` and `app.server`, scope `AgentStreamService` to `Scope.APP`, and standardize `create_container` across ASGI, CLI, and jobs

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `sqlspec-069-and-core-foundation` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - Retain `BaseStruct` and `CamelizedBaseStruct` in `src/app/lib/schema.py` during PR 1 so existing domain schemas continue to pass `make test-unit` until PR 2 (`domain-standardization-and-debloat`) completes the migration and removes them.
  - Scope `test_queue_settings.py` to `DatabaseSettings.get_queue_config()`, `QueueSettings`, and `plugins.queue` in Task `1.1`, and assert `await container.get(QueueService)` via `create_container()` in `test_ioc_and_services.py` in Task `1.4` so `files:` and `tests:` remain strictly disjoint.
- **Newest Discoveries**:
  1. `sqlspec.config` / `sqlspec.core` statement configuration supports wire-level `enable_sqlcommenter=True` alongside `driver_features={"enable_session_tracing": True}` on `OracleAsyncConfig`.
  2. `test_ioc_and_services.py:39-60` previously asserted legacy `EmbeddingService`, `ResponseCacheService`, and `SystemService` aliases; focusing `test_ioc_and_services.py` on Dishka container/provider behavior in Task `1.4` decouples IoC tests from PR 2's domain alias cleanup.
- **Blockers & Unblock Conditions**: None
- **Next Exact Step**: Claim and execute Task `1.1` (`tasks/1.1.md`).
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/platform-alignment-apex-vertex-prd/research/codebase-alignment-and-apex/research.md`
  - `.agents/bundles/knowledge/domains/core-lib-ioc-server-cli.md`
  - `.agents/bundles/knowledge/gotchas/oracle-sqlspec-and-queues.md`

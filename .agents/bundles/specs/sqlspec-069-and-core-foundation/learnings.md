---
type: Learnings
flow_id: sqlspec-069-and-core-foundation
title: SQLSpec 0.69.0 & Core Foundation Learnings
description: Implementation learnings and discoveries from upgrading to SQLSpec 0.69.0, frozen schemas, OracleLoaderService, and decoupled Dishka IoC.
---

# Learnings: `sqlspec-069-and-core-foundation`

## Task `1.1` — SQLSpec `0.69.0` Settings, Tracing, `wallet_zip` & Slotted Dataclasses (`9b64b7c`)

- **SQLSpec `0.69.0` `fetch_lobs` Default**: `OracleAsyncConfig` in `sqlspec==0.69.0` removes `enable_AutoLob` from `VALID_ORACLE_DRIVER_FEATURE_KEYS` and defaults `driver_features["fetch_lobs"]` to `False`, meaning LOB columns under 1 GB return inline `str`/`bytes` values across both `select` and `select_stream` instead of `oracledb.AsyncLOB` locators (`fetch_lobs=True` requests LOB locators). `DatabaseSettings.create_config()` sets `driver_features={"enable_session_tracing": True}` while `DatabaseSettings.get_queue_config()` isolates `litestar-queues` worker pool mutations on its dedicated `queue_db_session` pool (`min=1, max=4`).
- **Native Wallet Extraction**: Passing `"wallet_zip": str(Path(self.WALLET_LOCATION).resolve())` and `"wallet_password"` in `_build_pool_config` delegates PEM extraction and `config_dir` / `wallet_location` configuration to `sqlspec.adapters.oracledb.extract_oracle_wallet_zip` without mutating `os.environ["TNS_ADMIN"]` or disabling TLS hostname verification.

## Task `1.2` — Frozen Schemas, Centralized Serialization, `app.lib.exceptions` & `OracleLoaderService` (`ee2b3d3`)

- **`SQLFileLoader` Import Path & Dishka Constructor Signatures**: Import `SQLFileLoader` from `sqlspec.loader` (not `sqlspec.core`). Dishka's `provide(ServiceCls)` inspects every typed `__init__` parameter (including parameters with defaults) and rejects union types (`OracleAsyncDriver | OracleAsyncConfig`, `SQLFileLoader | None`). Using `def __init__(self, driver: OracleAsyncDriver, loader: SQLFileLoader = cast("SQLFileLoader", None)) -> None:` on `OracleLoaderService` (coupled with `_init_from_config(config, loader)` for app-scoped pool stores) satisfies both Dishka auto-wiring and single-argument unit tests (`ServiceCls(mock_driver)`).

## Task `1.3` — Logging Cleanup, `register_reset_hook` & Nested-Import Gates (`8af3e6e`)

- **Reset Hook Decoupling**: Registering `plugins._reset` via `app_config.register_reset_hook(_reset)` at module bottom in `src/app/server/plugins.py` eliminates circular function-scoped imports between `src/app/config.py` and `src/app/server/plugins.py`, allowing `ALLOWED_LAZY_IMPORT_FILES` (`tools/ci/check_code_hygiene.py`) and `ALLOW_NESTED_IMPORTS` (`src/tests/unit/test_test_suite_guards.py`) to restrict nested imports exclusively to `src/app/cli/{commands,main}.py`.

## Task `1.4` — Decoupled Dishka IoC & `Scope.APP` `AgentStreamService` (`d19c3e2`)

- **Composition-Root Pool & Queue Sharing**: Accepting optional `db_config`, `queue_config`, and `queue_plugin` keyword arguments on `DBProvider` and `create_container(...)` lets `src/app/server/asgi.py` share Litestar's lifespan-managed `OracleAsyncConfig` pools and `QueuePlugin` without any `app.config` or `app.server` import inside `src/app/ioc/`, while standalone CLI and background-job containers resolve directly from `Settings.from_env()`.

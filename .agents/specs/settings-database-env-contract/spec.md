# Flow: settings-database-env-contract

*Beads: oracledb-vertexai-mzm.4*

## Specification

Absorbs old PRD Chapter 3. Aligns the Oracle connection env contract across the
three places that independently parse `DATABASE_*`/`WALLET_*`/`TNS_ADMIN` today:
the app's `DatabaseSettings` (`src/app/lib/settings.py`), the tooling's
`ConnectionConfig.from_env()` (`tools/oracle/connection.py`), and the `.env`
generator (`tools/lib/utils.py`). One set of variable names and defaults, one
behavior. Container lifecycle config (`tools/oracle/database.py` `DatabaseConfig`)
stays SEPARATE — it owns image/ports/passwords/volumes for the managed container,
not app runtime connection.

### Requirements

1. Establish ONE app connection env contract shared (or mirrored consistently) by
   `DatabaseSettings`, `ConnectionConfig.from_env()`, and `.env` generation:
   - `DATABASE_USER` (default `app`)
   - `DATABASE_PASSWORD` (default `SuperSecret1`)
   - `DATABASE_HOST` (default `localhost`)
   - `DATABASE_PORT` (default `1521`)
   - `DATABASE_SERVICE_NAME` (default `myatp_low`)
   - `DATABASE_DSN` (derived `host:port/service_name` when unset)
   - `DATABASE_URL`, `WALLET_PASSWORD`, `WALLET_LOCATION`/`TNS_ADMIN` for wallet
     and autonomous modes
   - `DATABASE_POOL_MIN_SIZE` (default `5`), `DATABASE_POOL_MAX_SIZE` (default `20`)
2. Resolve the default-service-name and port DISCREPANCIES between the three
   sources so they agree:
   - `ConnectionConfig.from_env()` defaults external `service_name` to `ORCL`
     (`connection.py:110`) while `DatabaseSettings` defaults to `myatp_low`. Align
     to the managed/local default (`myatp_low`) for the demo's primary path; keep
     external-override behavior intact.
   - `ConnectionConfig.from_env()` reads `ORACLE26AI_PORT`/`ORACLE23AI_PORT`
     (`connection.py:108`) and `from_env` falls back through them; `DatabaseSettings`
     reads `DATABASE_PORT` only. Pick `DATABASE_PORT` as the canonical app
     connection port; container lifecycle keeps its own `ORACLE*_PORT` host-port
     knobs in `DatabaseConfig`.
   - `ConnectionConfig.from_env()` also reads legacy `ORACLE_USER`/`ORACLE_PASSWORD`
     (`connection.py:103-105`). Standardize on `DATABASE_USER`/`DATABASE_PASSWORD`
     for the app contract; drop the `ORACLE_*` fallbacks unless an existing test or
     connection path needs them (verify first).
3. Remove or genuinely wire pool knobs. `DatabaseSettings.POOL_TIMEOUT`,
   `POOL_RECYCLE`, and `ECHO` are never passed to `OracleAsyncConfig`
   (`settings.py:154-173`). After checking SQLSpec `OracleAsyncConfig` /
   `oracledb` pool kwargs:
   - If `oracledb`/SQLSpec supports a matching pool-timeout/recycle kwarg, wire it
     and add a test asserting it lands in `connection_config`.
   - Otherwise delete the knobs. (NOTE: these three are also slated for deletion in
     flow `settings-audit-and-factory` mzm.3 Phase 4.6 — coordinate so they are
     removed exactly once; whichever flow lands first owns the deletion.)
   Keep `POOL_MIN_SIZE`/`POOL_MAX_SIZE`, which ARE passed as `min`/`max`.
4. Keep the SQLSpec extension flags that are genuinely used and tested:
   `ADK_ENABLE_MEMORY` (`ADK_ENABLE_MEMORY` env), `ADK_IN_MEMORY`
   (`ORACLE_ADK_IN_MEMORY` env), `LITESTAR_SESSION_IN_MEMORY`
   (`ORACLE_LITESTAR_SESSION_IN_MEMORY` env). These have coverage in
   `src/tests/unit/app/lib/test_settings.py`.
5. Normalize service-name casing ONLY where existing tests and live connections
   stay valid. The demo standardizes on lowercase `myatp_low`; do not flip to
   `FREEPDB1`/`MYATP_LOW` casing that would break wallet `tnsnames.ora` resolution
   or the existing `test_service_name_defaults_to_myatp_low` assertion.
6. Preserve wallet/autonomous behavior exactly:
   `DatabaseSettings.is_autonomous` (URL + wallet password present),
   `get_connection_params()`, and the SSL/`TNS_ADMIN` wallet path in
   `create_config()` (`settings.py:136-164`) must be unchanged in semantics.
7. Keep container lifecycle config OUT of app settings.
   `tools/oracle/database.py` `DatabaseConfig` (image, host/container ports,
   admin/wallet/app/oee passwords, volume locations, health) is not moved into
   `DatabaseSettings` and is not read by the app at runtime.
8. Project rules: dataclasses only; no compat shims for removed env fallbacks;
   behavior-only docstrings; never log secrets, wallet passwords, or full
   connection URLs (note `database.py` already prints masked credentials —
   `.env` generation in `utils.py` must not log secret values to console).

### Code Analysis Summary

- `src/app/lib/settings.py` `DatabaseSettings`:
  - Env reads (lines 39-95): `DATABASE_URL`, `WALLET_PASSWORD`,
    `WALLET_LOCATION`/`TNS_ADMIN`, `DATABASE_USER` (`app`), `DATABASE_PASSWORD`
    (`SuperSecret1`), `DATABASE_HOST` (`localhost`), `DATABASE_PORT` (`1521`),
    `DATABASE_SERVICE_NAME` (`myatp_low`), `DATABASE_DSN` (derived),
    `DATABASE_POOL_MIN_SIZE` (5), `DATABASE_POOL_MAX_SIZE` (20),
    `DATABASE_POOL_TIMEOUT` (30, UNUSED), `DATABASE_POOL_RECYCLE` (300, UNUSED),
    `DATABASE_ECHO` (UNUSED), `ORACLE_ADK_IN_MEMORY`, `ADK_ENABLE_MEMORY`,
    `ORACLE_LITESTAR_SESSION_IN_MEMORY`, `DATABASE_MIGRATION_PATH`.
  - `create_config()` passes only `user/password/dsn/min/max` (+ wallet keys) into
    `connection_config`; pool timeout/recycle/echo never reach the driver.
- `tools/oracle/connection.py` `ConnectionConfig.from_env()` (lines 51-123):
  - Defaults differ: external `service_name` -> `ORCL` (line 110); managed ->
    `myatp_low`. Reads `ORACLE_USER`/`ORACLE_PASSWORD` fallbacks (103-105) and
    `ORACLE26AI_PORT`/`ORACLE23AI_PORT` (108). Parses `DATABASE_URL` regex
    `oracle\+oracledb://user:password@service` (90-101).
  - `detect_deployment_mode()` (579-598): EXTERNAL when `DATABASE_HOST` or
    `DATABASE_URL` set, else MANAGED. This is a tooling concept, not app settings.
- `tools/oracle/database.py` `DatabaseConfig.from_env()` (lines 104-130): container
  lifecycle only — `ORACLE_SYSTEM_PASSWORD`, `WALLET_PASSWORD`, `TNS_ADMIN`/
  `WALLET_LOCATION`, `ORACLE26AI_PORT`/`ORACLE23AI_PORT`, mtls/https/mongo ports,
  `DATABASE_USER`/`DATABASE_PASSWORD` (for the app user it creates), `OEE_PASSWORD`,
  `WORKLOAD_TYPE`, data/audit/oradata locations. STAYS SEPARATE.
- `tools/lib/utils.py` `create_env_interactive()` (lines 51-187): hand-writes the
  `.env`. Drift to fix: emits `GOOGLE_PROJECT_ID` (line 162) and
  `VERTEX_AI_PROJECT_ID=${GOOGLE_PROJECT_ID}` (165) but never `DATABASE_HOST`/
  `DATABASE_PORT` for managed mode (only `DATABASE_SERVICE_NAME` + `DATABASE_URL`);
  external standard mode writes `DATABASE_HOST`/`PORT`/`SERVICE_NAME`. Align the
  generated keys/defaults with the `DatabaseSettings` contract above.
- Existing tests to keep green: `test_oracle_adk_and_litestar_session_flags_*`,
  `test_oracle_adk_and_litestar_session_in_memory_default_to_true`,
  `test_wallet_location_resolves_to_absolute_path`,
  `test_service_name_defaults_to_myatp_low` in
  `src/tests/unit/app/lib/test_settings.py`; plus
  `src/tests/unit/tools/oracle/test_database.py` and any
  `src/tests/integration/tools/oracle/` connection tests.

## Implementation Plan

### Phase 1: Lock the contract with tests

- [x] 1.1 In `src/tests/unit/app/lib/test_settings.py`, add
      `test_database_settings_local_contract`: with `DATABASE_*` unset, assert
      `DatabaseSettings()` yields `user=app`, `password=SuperSecret1`,
      `host=localhost`, `port=1521`, `service_name=freepdb1`, derived
      `dsn=localhost:1521/freepdb1`, `pool_min=5`, `pool_max=20`. [31485ce]
      (Corrected to `freepdb1`: that is the gvenzl PDB and the managed/local
      target; `myatp_low` is only the wallet TNS alias from `DATABASE_URL`.)
- [x] 1.2 Add `test_connection_config_matches_database_settings_defaults` in
      `src/tests/unit/tools/oracle/test_connection.py` (connection test module,
      kept away from the dirty `test_database.py`): with env cleared, assert
      `ConnectionConfig.from_env()` resolves the SAME user/host/port/service_name
      defaults as `DatabaseSettings` for managed mode. The required RED drift test;
      failed on `service_name` (`myatp_low` vs `freepdb1`). [31485ce]
- [x] 1.3 Add `test_wallet_mode_contract`: with `DATABASE_URL` + `WALLET_PASSWORD`
      + `TNS_ADMIN` set, assert `DatabaseSettings.is_autonomous` is True and
      `create_config()` populates wallet keys. [31485ce]
- [x] 1.4 Ran; confirmed 1.1 + 1.2 RED for the documented drift, 1.3 + existing
      tests GREEN. RED list recorded in Beads note. [31485ce]

### Phase 2: Align ConnectionConfig with the app contract

- [x] 2.1 In `tools/oracle/connection.py`, changed the managed + external default
      `service_name` from `myatp_low`/`ORCL` to `freepdb1` so the three readers
      agree; kept explicit-override behavior. `for_external` default also aligned. [31485ce]
- [x] 2.2 Standardized the connection port on `DATABASE_PORT`. Dropped the
      `ORACLE26AI_PORT`/`ORACLE23AI_PORT` fallbacks from `ConnectionConfig.from_env()`
      — those host-port knobs stay in container lifecycle (`database.py`). Verified
      no test relied on them for app connection. [31485ce]
- [x] 2.3 Dropped the `ORACLE_USER`/`ORACLE_PASSWORD` fallbacks in favor of
      `DATABASE_USER`/`DATABASE_PASSWORD`; confirmed 0 tests/connections depend on
      them (`ORACLE_PASSWORD` is only used by the separate `database.py` lifecycle). [31485ce]
- [x] 2.4 Re-ran Phase 1; 1.1 + 1.2 turned GREEN. [31485ce]

### Phase 3: Resolve pool knobs

- [x] 3.1 Checked: `POOL_TIMEOUT`/`POOL_RECYCLE`/`ECHO` were already removed by
      Ch3 (mzm.3); none remain in `settings.py`. Verify-only. [31485ce]
- [x] 3.2 No knobs to delete or wire — Ch3 owned the deletion. [31485ce]
- [x] 3.3 Confirmed `POOL_MIN_SIZE`/`POOL_MAX_SIZE` stay wired as `min`/`max`. [31485ce]

### Phase 4: Align .env generation

- [x] 4.1 `tools/lib/utils.py` `create_env_interactive()` managed block already
      emits the canonical wallet contract; generated managed `.env` is byte-identical
      to the live working `.env` DB keys. External standard block already emits
      `DATABASE_USER/PASSWORD/HOST/PORT/SERVICE_NAME`. No change required. [31485ce]
- [x] 4.2 Verified generated values do not log secrets to console (`password=True`
      on sensitive prompts; file-only writes). [31485ce]
- [x] 4.3 AI project key reconciliation left to mzm.8 per spec; not a DB key. [31485ce]

### Phase 5: Verify

- [x] 5.1 `uv run pytest src/tests/unit/app/lib src/tests/unit/tools/oracle`:
      130 passed; only the 2 pre-existing `test_database.py` failures (unrelated
      dirty `cli/database.py`) remain — no new failures. [31485ce]
- [x] 5.2 Wallet/autonomous `create_config()` semantics unchanged
      (`test_wallet_location_resolves_to_absolute_path` green; live wallet
      `SELECT 1` succeeds; chat workflow integration test passes). [31485ce]
- [x] 5.3 `make lint` passes; `git diff --check` clean. [31485ce]

## Acceptance

- [x] `DatabaseSettings`, `ConnectionConfig.from_env()`, and `.env` generation
      resolve the same connection env variable names and defaults for the managed/
      local path (`freepdb1`). [31485ce]
- [x] App startup, `coffee upgrade`/fixtures, and
      `python manage.py database upgrade` resolve one connection contract (no
      `ORCL` vs `freepdb1` or `ORACLE*_PORT` vs `DATABASE_PORT` divergence on the
      app path). [31485ce]
- [x] Wallet/autonomous behavior is byte-for-byte preserved in semantics
      (live wallet `SELECT 1` + chat integration test pass). [31485ce]
- [x] No unused database pool knob remains in settings (Ch3 removed
      `POOL_TIMEOUT`/`POOL_RECYCLE`/`ECHO`; `min`/`max` stay wired). [31485ce]
- [x] Container lifecycle config stays in `tools/oracle/database.py` and is not
      read by app runtime settings. [31485ce]
- [x] Service name stays `freepdb1` (managed/local) / `myatp_low` (wallet alias);
      existing service-name/wallet tests still pass. [31485ce]
- [x] No compat shim for removed `ORACLE_*` fallbacks; behavior-only docstrings;
      no secret/URL logging added. [31485ce]

## Verification

```bash
uv run pytest src/tests/unit/app/lib src/tests/unit/tools/oracle
make lint
git diff --check
```

```bash
# Confirm contract alignment and that container config stayed separate
grep -n "service_name\|DATABASE_PORT\|ORACLE26AI_PORT\|ORACLE_USER" tools/oracle/connection.py
grep -n "POOL_TIMEOUT\|POOL_RECYCLE\|ECHO" src/app/lib/settings.py
```

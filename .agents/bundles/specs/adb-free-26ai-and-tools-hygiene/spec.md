---
type: Spec
flow_id: adb-free-26ai-and-tools-hygiene
title: Autonomous AI Database Free 26ai Runtime, Legacy APEX Sidecar Retirement, Cloud Run ORDS Packaging, and Tools Hygiene
state: completed
plan_revision: 1
plan_commit: "7ff2771"
state_revision: 4
current_task: null
last_operation: complete
operation_targets:
  - "3.1"
  - "3.2"
  - "3.3"
  - "3.4"
last_verified_checkpoint: "ccbc652"
created_at: 2026-10-24T19:35:00Z
updated_at: 2026-10-25T17:14:00Z
description: Third stacked PR making container-registry.oracle.com/database/adb-free:latest-26ai (APEX 26.1.5 + ORDS 26.3) the default managed development runtime with automated mTLS wallet export and ADMIN schema provisioning, retiring legacy gvenzl SYSDBA APEX/ORDS/health modules while keeping gvenzl/oracle-free for integration tests, packaging Cloud Run ORDS CDN SQL inside the app wheel, and enforcing check_code_hygiene.py across tools/ and manage.py.
tags:
  - oracle-26ai
  - adb-free
  - apex
  - tools
  - hygiene
parent_prd: platform-alignment-apex-vertex-prd
research: []
---

# Flow: Autonomous AI Database Free 26ai Runtime, Legacy APEX Sidecar Retirement, Cloud Run ORDS Packaging, and Tools Hygiene

**Flow ID:** `adb-free-26ai-and-tools-hygiene`
**Parent PRD:** [`platform-alignment-apex-vertex-prd`](../platform-alignment-apex-vertex-prd/spec.md)
**Depends On:** [`domain-standardization-and-debloat`](../domain-standardization-and-debloat/spec.md) (PR 3 of 5 in stack)
**Proposed Branch & PR Title:** `feat/adb-free-26ai-runtime` — `feat(infra): adopt adb-free 26ai runtime, retire legacy apex sidecar, and enforce tools hygiene`

---

## Specification

### Code Analysis Summary

Files examined:

- `tools/oracle/database.py:1-795` & `tools/oracle/container.py:1-278` — `DatabaseConfig` hardcodes `gvenzl/oracle-free:latest` (`oracle-free-db`, `:1521/freepdb1`), and `ContainerRuntime.container_exists` (`container.py:156-165`) runs `docker ps -a` twice per lookup.
- `tools/oracle/wallet.py:1-512` & `tools/oracle/connection.py:1-610` — `wallet.py:450` prints `DATABASE_USERNAME` instead of `DATABASE_USER` and extracts wallet archives manually instead of reusing `sqlspec.adapters.oracledb.{extract_oracle_wallet_zip,parse_tnsnames_ora}`; `connection.py:59-86` classifies any `DATABASE_URL` or `DATABASE_HOST` setting as `DeploymentMode.EXTERNAL`, misclassifying managed `adb-free` wallet DSNs (`myatp_low`).
- `tools/oracle/{apex_media,apex_install,ords,health}.py` & `tools/oracle/cli/{ords,health,sqlcl}.py` — Legacy ~1,800-line SYSDBA `apxins.sql` installer and separate `container-registry.oracle.com/database/ords` sidecar built for `gvenzl/oracle-free` before `adb-free:latest-26ai` shipped APEX 26.1.5 + ORDS 26.3 pre-installed on `:8443`.
- `tools/oracle/apex_lang.py:28-192`, `tools/oracle/apex_catalog.py:80-94`, `tools/oracle/cli/{apex,database}.py`, `manage.py:1-95` — `ApexLang._connect_line` only builds EasyConnect `//host:port/freepdb1` strings without `TNS_ADMIN` wallet aliases (`myatp_low`); `apex_catalog.py` defaults to `http://localhost:8000` (unreachable from inside the `adb-free` container instead of `http://host.docker.internal:8000`); `manage.py:83` wires `oracle_ords_group` and uses function-scoped imports.
- `src/app/cli/_helpers/ords.py:48`, `tools/deploy/gcp/{configure-apex-cdn,revert-apex-cdn}.sql`, `tools/deploy/docker/Dockerfile:43-88`, `tools/deploy/gcp/cloudbuild.yaml:38-89` — `configure_apex_cdn_helper` looks up `BASE_DIR.parents[1] / "tools" / "deploy" / "gcp" / "configure-apex-cdn.sql"`, which raises `FileNotFoundError` inside distroless Cloud Run PyApp builds where `tools/` is excluded from the wheel (`pyproject.toml:138` packages `src/app/**/*.sql`).
- `tools/cli/install.py:306-316` & `tools/lib/utils.py:170,295-420` — `install_sqlcl_with_config` iterates `for instruction in installer.get_path_instructions():` over a `str` return value (`sqlcl_installer.py:401`), printing one character per line; `utils.py:170` writes `LITESTAR_PORT=5006` instead of `8000` and carries 125 lines of unused `is_antigravity_mcp_server_configured` / `configure_sqlcl_connection_with_password` helpers (`lines 295-420`).
- `tools/ci/check_code_hygiene.py:13-116` — Scans only `src/app`, `tools/slides`, `tools/ci`, and inline comments in `manage.py`, leaving `tools/oracle`, `tools/cli`, `tools/lib`, `tools/scripts`, `tools/bundler.py`, and `tools/license_headers.py` unchecked.

### Relevant Patterns

- [Core Platform (`lib/`, `ioc/`, `server/`, `cli/`)](../../knowledge/domains/core-lib-ioc-server-cli.md) — `Settings.from_env()` wallet configuration (`DATABASE_URL=myatp_low`, `WALLET_LOCATION`, `WALLET_PASSWORD`) and CLI subcommand boundaries.
- [Operational Patterns](../../knowledge/patterns/operations.md) — Idempotent infrastructure lifecycle commands and explicit credential handling.
- [Testing Rulebook](../../../../src/tests/AGENTS.md) — Keep integration tests isolated on ephemeral `gvenzl/oracle-free:latest` (`ORACLE_CONTAINER_FLAVOR=free`); keep unit tests database-free under `src/tests/unit/tools/test_*.py`.

### Requirements

- **PLAT-REQ-09 (Managed `adb-free:latest-26ai` Container, Wallet Export & `ADMIN` Schema Bootstrap)**:
  - Default `ORACLE_CONTAINER_FLAVOR=adb-free` in `DatabaseConfig` (`tools/oracle/database.py`) using `container-registry.oracle.com/database/adb-free:latest-26ai` (`cymbal-adb-free`, ports `1521:1522`, `1522:1522`, `8443:8443`, `WORKLOAD_TYPE=ATP`, `ENABLE_ARCHIVE_LOG=FALSE`, `--cap-add SYS_ADMIN --device /dev/fuse`, named volume `cymbal-adb-data:/u01/data`, `--add-host=host.docker.internal:host-gateway` on Linux Docker), with preflight port-collision refusal when a legacy `oracle-free-db` container holds `:1521` and single-call `container_exists` in `tools/oracle/container.py`.
  - Add `tools/oracle/adb.py` exporting `/u01/app/oracle/wallets/tls_wallet` from `cymbal-adb-free` into `WALLET_LOCATION` (`.envs/tns`) validated via `sqlspec.adapters.oracledb.{extract_oracle_wallet_zip,parse_tnsnames_ora}`, and running idempotent `ADMIN` provisioning (`APP` user with `CONNECT`, `RESOURCE`, `CONSOLE_DEVELOPER`, `DWROLE`, `DB_DEVELOPER_ROLE`, `UNLIMITED TABLESPACE`, `EXECUTE ON DBMS_CLOUD_AI`, `ORDS.ENABLE_SCHEMA`, and `COFFEE` APEX workspace mapped to `APP`).
  - Fix `DATABASE_USER` in `tools/oracle/wallet.py:450`, support explicit `DATABASE_DEPLOYMENT_MODE=managed|external` in `tools/oracle/connection.py` so managed `myatp_low` wallet setups report `DeploymentMode.MANAGED`, and pin `ORACLE_CONTAINER_FLAVOR="free"` in `src/tests/integration/conftest.py` while keeping `tools/oracle/on_init/*.sql` and `tools/oracle/on_startup/*.sql` intact for `free` flavor and GCE Terraform VM setups.
- **PLAT-REQ-10 (Retire Legacy `gvenzl` APEX/ORDS/Health/SQLcl Modules & Update Wallet-Aware APEX Tooling)**:
  - Delete `tools/oracle/{apex_media,apex_install,ords,health}.py` and `tools/oracle/cli/{ords,health,sqlcl}.py`, updating `tools/oracle/__init__.py`, `tools/oracle/cli/__init__.py`, and `manage.py` (removing `oracle_ords_group` and top-levelizing imports in `manage.py`).
  - Update `tools/oracle/apex_lang.py` (`@dataclass(slots=True)`, `TNS_ADMIN` environment injection and `user/password@myatp_low` wallet connect strings when `wallet_location` is configured), `tools/oracle/apex_catalog.py` (`http://host.docker.internal:8000` default container-reachable server URL and `app.utils.serialization`), `tools/oracle/cli/apex.py` (`status` querying `APEX_RELEASE` and probing `https://localhost:8443/ords/` without `install`/`upgrade` subcommands), and `tools/oracle/cli/database.py` (printing APEX Builder, Database Actions, wallet path, and `myatp_low` status).
- **PLAT-REQ-11 (Cloud Run ORDS CDN SQL Packaging & `tools/cli/` / `tools/lib/utils.py` Defect Fixes)**:
  - Move `configure-apex-cdn.sql` and `revert-apex-cdn.sql` from `tools/deploy/gcp/` into `src/app/db/sql/deploy/` so Hatch includes them in the wheel (`src/app/**/*.sql`), update `src/app/cli/_helpers/ords.py` to resolve `BASE_DIR / "db" / "sql" / "deploy" / "configure-apex-cdn.sql"` (`Settings.from_env()`, wallet/ADMIN or SYSDBA connection support), and verify `tools/deploy/docker/Dockerfile` and `tools/deploy/gcp/cloudbuild.yaml` job compatibility.
  - Fix character-by-character iteration over `installer.get_path_instructions()` in `tools/cli/install.py:314`, update `tools/lib/utils.py` (`LITESTAR_PORT=8000`, `DATABASE_DEPLOYMENT_MODE=managed`, `adb-free` wallet `.env` defaults, `app.utils.serialization`, deleting dead lines `295-420`), and update `tools/cli/{init,doctor}.py` for `adb-free:latest-26ai` resource and wallet diagnostics.
- **PLAT-REQ-12 (Repo-Wide `tools/` Hygiene Cleanup & `check_code_hygiene.py` Gate Expansion)**:
  - Eliminate all inline `#` comments, function-scoped imports, and missing `slots=True` / package `__init__.py` docstrings across `tools/oracle/{sqlcl_installer.py,cli/connection.py,cli/wallet.py}`, `tools/bundler.py`, `tools/license_headers.py`, `tools/scripts/{__init__.py,generate_inventory_fixtures.py}`, `tools/__init__.py`, and `tools/lib/__init__.py`; update `Makefile` (`start-infra` reusing `cymbal-adb-free` without `--recreate --skip-apex --skip-ords`, `apex` printing status/URLs).
  - Expand `tools/ci/check_code_hygiene.py` to run both `check_inline_comments` and `check_ast_rules` across all of `src/app/**/*.py`, `tools/**/*.py`, and `manage.py`.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `PLAT-REQ-09` | `3.1` | `behavior_tdd` | `tools/oracle/{adb,container,database,wallet,connection}.py`, `src/tests/integration/conftest.py` | `src/tests/unit/tools/test_adb_and_wallet.py` |
| `PLAT-REQ-10` | `3.2` | `behavior_tdd` | `tools/oracle/{__init__,apex_lang,apex_catalog}.py`, `tools/oracle/cli/{__init__,apex,database}.py`, `manage.py` (+ 7 deleted legacy modules) | `src/tests/unit/tools/test_apex_tooling.py` |
| `PLAT-REQ-11` | `3.3` | `behavior_tdd` | `src/app/db/sql/deploy/{configure-apex-cdn,revert-apex-cdn}.sql`, `src/app/cli/_helpers/ords.py`, `tools/deploy/{docker/Dockerfile,gcp/cloudbuild.yaml}`, `tools/cli/{install,init,doctor}.py`, `tools/lib/utils.py` | `src/tests/unit/tools/test_cli_and_ords_deploy.py`, `src/tests/unit/cli/test_commands.py` |
| `PLAT-REQ-12` | `3.4` | `static_validation` | `Makefile`, `tools/{__init__,bundler,license_headers}.py`, `tools/lib/__init__.py`, `tools/scripts/{__init__,generate_inventory_fixtures}.py`, `tools/oracle/{sqlcl_installer,cli/connection,cli/wallet}.py`, `tools/ci/check_code_hygiene.py` | `src/tests/unit/tools/test_code_hygiene_gate.py` |

---

## Implementation Plan

### Phase 1: `adb-free:latest-26ai` Runtime, Legacy APEX/ORDS Retirement, Cloud Run Packaging & Tools Hygiene

- [x] 3.1 Add `adb-free:latest-26ai` container lifecycle, SQLSpec wallet export, `ADMIN` schema/workspace bootstrap, and `free`-flavor integration test isolation
- [x] 3.2 Delete retired `gvenzl` APEX/ORDS/health/SQLcl modules and update wallet-aware `ApexLang`, `ApexCatalog`, `manage.py`, and `infra` CLI commands
- [x] 3.3 Package Cloud Run ORDS CDN SQL under `src/app/db/sql/deploy/` and fix `tools/cli/` and `tools/lib/utils.py` defects
- [x] 3.4 Clean remaining `tools/` modules, update `Makefile` `adb-free` targets, and expand `tools/ci/check_code_hygiene.py` repo-wide

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `adb-free-26ai-and-tools-hygiene` (`completed`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `ccbc652`
- **Key Decisions**:
  - Consolidate all 7 legacy `tools/oracle/` deletions and `tools/oracle/{__init__,cli/__init__}.py` + `manage.py` rewiring into Task `3.2` so Task `3.4` owns a strictly disjoint file set when expanding `check_code_hygiene.py` across `tools/**/*.py` and `manage.py`.
  - Retain `tools/oracle/on_init/*.sql` and `tools/oracle/on_startup/*.sql` intact because `ORACLE_CONTAINER_FLAVOR=free` (`make test-integration`) and `tools/deploy/terraform/db_vm.tf` consume them.
- **Newest Discoveries**:
  1. `SQLclInstaller.get_path_instructions()` (`tools/oracle/sqlcl_installer.py`) returns `str`, so `tools/cli/install.py` now iterates `.splitlines()` instead of printing one character per line.
  2. Moving `configure-apex-cdn.sql` and `revert-apex-cdn.sql` into `src/app/db/sql/deploy/` leverages Hatch's `src/app/**/*.sql` wheel inclusion rule and supports both `ADMIN` + wallet and `SYSDBA` connections.
  3. `tools/ci/check_code_hygiene.py` now checks all 155 Python files across `src/app/`, `tools/`, and `manage.py` for zero inline `#` comments and AST rules.
- **Blockers & Unblock Conditions**: None.
- **Next Exact Step**: Branch `feat/apex-26-vertex-ai` from `feat/adb-free-26ai-runtime` and execute `apex-26-vertex-ai-and-app` Tasks `4.1`–`4.3`.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: "7ff2771"`
- **State Identity**: `state_revision: 4`, `last_operation: complete`, `operation_targets: ["3.1", "3.2", "3.3", "3.4"]`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/platform-alignment-apex-vertex-prd/research/codebase-alignment-and-apex/research.md`
  - `.agents/bundles/knowledge/patterns/operations.md`
  - `src/tests/AGENTS.md`

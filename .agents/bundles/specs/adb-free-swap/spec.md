---
type: Spec
flow_id: adb-free-swap
title: Swap the managed dev database to Oracle Autonomous AI Database Free 26ai
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-10-13T19:15:00Z
updated_at: 2026-10-13T19:15:00Z
description: Make the ADB-Free 26ai container the default managed database with an mTLS wallet, ADMIN-only provisioning, and Select AI, keep gvenzl as the integration-test and terraform backend, and settle vector-memory and In-Memory behavior with live evidence.
tags:
  - migration
  - oracle-26ai
  - infrastructure
  - select-ai
parent_prd: null
research:
  - research/adb-free-evidence.md
---

# Flow: Swap the Managed Dev Database to Oracle Autonomous AI Database Free 26ai

**Flow ID:** `adb-free-swap`
**Parent PRD:** none
**Pauses:** `apex-ops-console`, `apex-ops-app`, `apex-demo-verification-docs` (user decision, 2026-10-13)

## North Star

`make start-infra && uv run coffee upgrade && uv run coffee run` runs Cymbal Coffee against a local Oracle Autonomous AI Database Free 26ai container over an mTLS wallet, the same connection shape the app uses for Autonomous AI Database on Oracle Database@Google Cloud. The DBA talk's Select AI, `DBMS_CLOUD` credential, and wallet/TCPS examples run live against it. The ephemeral gvenzl container stays the fast integration-test backend.

## Specification

### Background

- June 2026 (`f360c2f`, `1c75677`, `a7b9112`) ran `adb-free:latest-26ai` with wallet authentication and an ADMIN-created app user. The demo left it on 2026-06-14 (`56cb007`; rationale in `git show 900d04d:.agents/specs/apex-gvenzl-install/prd.md`): the image shipped APEX 24.2.14, `sqlplus / as sysdba` failed with ORA-01017, and no in-container APEX upgrade path exists.
- The user now values real Select AI (`DBMS_CLOUD_AI`), `DBMS_CLOUD`, and wallet/TCPS connections over APEX 26.1, and pauses the APEX console work.
- Evidence, citations, contradictions, and limitations: [research/adb-free-evidence.md](research/adb-free-evidence.md).

### Code Analysis Summary

| Path | Finding |
| --- | --- |
| `tools/oracle/database.py` | gvenzl-only lifecycle (`DEFAULT_IMAGE = "gvenzl/oracle-free:latest"`, container `oracle-free-db`, volume `oracle-db-data`); mounts `tools/oracle/on_init` and `on_startup` into gvenzl hook directories; repairs the app user with in-container SYSDBA. Contains inline `#` comments. |
| `tools/oracle/on_init/*.sql`, `tools/oracle/on_startup/*.sql` | SYSDBA hooks (512M vector pool plus bounce, grants). Also read by `tools/deploy/terraform/db_vm.tf`. |
| `tools/oracle/cli/database.py` | `infra start` auto-installs APEX and starts the ORDS sidecar unless skipped; `stop`, `remove`, and `status` always touch the ORDS sidecar. |
| `tools/oracle/cli/apex.py`, `tools/oracle/cli/ords.py` | APEX 26.1 installer (SYSDBA) and ORDS sidecar commands; APEXlang SQLcl commands share the `apex` group. |
| `tools/oracle/container.py` | `ContainerRuntime.run_command()` for Docker and Podman, including `cp`. |
| `tools/oracle/wallet.py` | `WalletConfigurator.validate_wallet()` and alias parsing. |
| `tools/oracle/connection.py` | `ConnectionConfig.from_env()` handles `DATABASE_URL` plus wallet; has its own `detect_deployment_mode()`. |
| `tools/lib/utils.py` | Managed `.env` writes `freepdb1`; `detect_deployment_mode()` treats any `DATABASE_URL` as external; SQLcl saved connection supports host/port/service only. |
| `tools/cli/doctor.py`, `tools/cli/init.py` | Managed checks (runtime; the memory warning already names the ADB container) and next-step text. |
| `src/app/lib/settings/_database.py` | Wallet mode (`is_autonomous` = `DATABASE_URL` and `WALLET_PASSWORD`) builds `wallet_location`, `config_dir`, `wallet_password`, and `ssl_context` for the app pool and the separate `get_queue_config()` pool. No change required. |
| `src/app/db/migrations/0001_cymball_coffee_products.sql` | `INMEMORY PRIORITY HIGH` on `product`, `response_cache`, `embedding_cache`, `chat_route`; HNSW on `product` and `chat_route`; `CTX_DDL` preferences and three `CTXSYS.CONTEXT` indexes. |
| `src/tests/integration/conftest.py` | Ephemeral gvenzl container per session (`oracle_test_container`). |
| `src/tests/conftest.py` | Root `.env.testing` already uses ADB wallet values (`myatp_low`, `TNS_ADMIN=.envs/tns`). |
| `src/tests/unit/test_test_suite_guards.py` | Bans `src/tests/unit/tools/oracle/`; three-conftest ratchet; no inline comments or nested imports in tests. |
| `.github/workflows/ci.yml` | CI runs unit tests only. |
| `Makefile` | `start-infra` passes `--recreate`; `test` and `test-integration` collect `src/tests/integration`. |
| `docs/reference/quickstart.md`, `docs/reference/developers.md` | Stale: quickstart already claims ADB and OEE; developers claims `pytest-databases`. |
| `.agents/bundles/knowledge/presentation/verified-facts.md` | Records `DBMS_CLOUD_AI` absent from gvenzl and the Select AI Google provider facts. |

### Relevant Patterns

- [Operations Patterns](../../knowledge/patterns/operations.md): vector pool sizing, optional APEX/ORDS.
- [Oracle 26ai, SQLSpec & Queues Gotchas](../../knowledge/gotchas/oracle-sqlspec-and-queues.md): queue pool LOB isolation, HNSW `FETCH APPROX`.
- [Testing Patterns](../../knowledge/patterns/testing.md) and `src/tests/AGENTS.md`: placement ladder, 5-section layout, conftest ratchet.
- [Code Style Patterns](../../knowledge/patterns/code-style.md): SPDX headers, PEP 604/585, docstrings, no inline comments.

### Scope

In scope: managed container lifecycle and wallet export; ADMIN provisioning; CLI and Makefile routing; managed `.env`, mode detection, doctor, and SQLcl wallet connection; the opt-in ADB acceptance suite; the In-Memory check; Select AI setup; docs and knowledge.

Out of scope: terraform, Cloud Run, and COS VM deployment (stays gvenzl); APEX 26.1 on ADB-Free; Oracle Estate Explorer; the Mongo API port; `DBMS_VECTOR` to Vertex AI ACLs; CI integration tests; migration DDL changes.

### Decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D1 | Default image `container-registry.oracle.com/database/adb-free:latest-26ai`; `ORACLE_IMAGE` overrides it (the README uses `ghcr.io/oracle/adb-free:latest-26ai`). | User choice. Task 1.1 records the resolved digest. |
| D2 | One `OracleDatabase` interface with two container flavors selected by `ORACLE_CONTAINER_FLAVOR`: `adb-free` (default) and `free` (gvenzl). | gvenzl still serves integration tests, the terraform VM, and the paused APEX 26.1 installer. This supersedes the June rule against dual adb-free/gvenzl paths. |
| D3 | `make test-integration` and `make test` keep the ephemeral gvenzl container; ADB contracts run in an opt-in suite (`make test-adb`, `ORACLE_ADB_ACCEPTANCE=1`) against the running dev container. | A per-session ADB container costs minutes and 8 GiB; CI runs unit tests only. |
| D4 | The wallet reaches the host by `cp` from `/u01/app/oracle/wallets/tls_wallet` into `WALLET_LOCATION` (default `.envs/tns`, gitignored) on every start, and `sqlnet.ora` DIRECTORY is rewritten to the absolute path. No wallet bind mount, `chmod 777`, or busybox helper. | README-documented; avoids the rootless uid and SELinux problems the June bind mount needed workarounds for. |
| D5 | Data lives in the named volume `cymbal-adb-data` at `/u01/data`. No `/dev/shm`, audit, or oradata mounts. | README-documented persistence; June's tmpfs mounts lost data on reboot. |
| D6 | The app connects with the mTLS alias `myatp_low` through the existing `DatabaseSettings` wallet path; the queue pool stays separate. | Existing ADB code path; matches Autonomous AI Database on Oracle Database@Google Cloud. |
| D7 | `DATABASE_DEPLOYMENT_MODE=managed\|external` makes the mode explicit; the existing heuristic stays as the fallback. | Managed ADB needs `DATABASE_URL`, which the heuristic reads as external. |
| D8 | The ADB path never uses SYSDBA, and vector memory is not configured on ADB-Free (elastic pool); the free flavor keeps the 512M hook. | ORA-01017 in June; research F10. |
| D9 | ADMIN grants `CONNECT, RESOURCE, CONSOLE_DEVELOPER, DWROLE, DB_DEVELOPER_ROLE`, `QUOTA UNLIMITED ON DATA`, `EXECUTE ON DBMS_CLOUD_AI`, an HTTP ACE for `generativelanguage.googleapis.com`, and `ORDS.ENABLE_SCHEMA`. | README recipe plus Oracle Text (`DB_DEVELOPER_ROLE` nests `CTXAPP`) plus Select AI prerequisites. |
| D10 | `make start-infra` reuses the container (drops `--recreate`); `make wipe-infra` is the clean slate. | The first ADB start takes minutes; recreate semantics depend on volume reattach, verified in Task 1.1. |
| D11 | Select AI reads its key only from `SELECT_AI_GEMINI_API_KEY` (no `GOOGLE_API_KEY` fallback); profile `COFFEE_GEMINI`, credential `GEMINI_CRED`, default model `gemini-3.5-flash`, object list = the app schema. | Matches slide 13; avoids sending a Vertex express key to the Gemini API. |
| D12 | The terraform VM and Cloud Run lab stay on gvenzl; the single-VM GCE lab inherits ADB-Free through `make start-infra`. | Cloud deploy needs wallet secrets, VM sizing, and ORDS removal: a separate flow. |
| D13 | APEX 26.1 work is paused: `infra apex install\|upgrade\|status` and `infra ords *` refuse on ADB-Free and name the free-flavor alternative; APEXlang SQLcl commands are untouched. | User decision; the installer stays intact for later. |

### Requirements

- **ADB-REQ-01 Managed ADB-Free lifecycle**: `OracleDatabase.start()` and `make start-infra` run the D1 image with the README run contract (ports `1521:1522`, `1522:1522`, `8443:8443`; `WORKLOAD_TYPE=ATP`, `ADMIN_PASSWORD`, `WALLET_PASSWORD`, `ENABLE_ARCHIVE_LOG=FALSE`; `--cap-add SYS_ADMIN --device /dev/fuse`; `cymbal-adb-data:/u01/data`; listener health check with a 600-second start period; 900-second startup timeout). They reuse the container on every path and refuse to start while the legacy `oracle-free-db` container exists.
- **ADB-REQ-02 Wallet export**: every ADB start exports and validates the wallet per D4 (`cwallet.sso`, `ewallet.pem`, `tnsnames.ora`, `sqlnet.ora`, alias `myatp_low`).
- **ADB-REQ-03 ADMIN provisioning**: every ADB start provisions the app user per D9 over the wallet as ADMIN, idempotently, with bounded connection retry and ORA-28007 handling. ADMIN, app, and wallet passwords pass the ADB policy check before any container mutation. No password appears in output or errors.
- **ADB-REQ-04 CLI and Makefile routing**: on ADB-Free, `infra start` skips APEX and ORDS and prints the APEX, Database Actions, wallet, and alias details; `stop`, `remove`, and `status` never touch the ORDS sidecar; D13 refusals apply; `make start-infra` follows D10.
- **ADB-REQ-05 Managed environment**: `manage.py init --mode managed` writes the ADB wallet block with `DATABASE_DEPLOYMENT_MODE=managed`. Mode detection follows D7 in `tools/lib/utils.py` and `tools/oracle/connection.py`. Doctor warns on fewer than 4 CPUs, less than 8 GiB, or a missing wallet. The SQLcl saved connection uses `app/<password>@myatp_low` with `TNS_ADMIN`. The generated `.env` yields wallet-mode app and queue pools with LOB isolation intact.
- **ADB-REQ-06 Runtime acceptance**: an opt-in suite proves the wallet app pool (`tcps`, user `APP`), the separate queue pool, valid HNSW and Oracle Text indexes after `coffee upgrade`, a non-zero elastic vector pool, HNSW and hybrid RRF queries, walletless TLS behavior, and refusal of a wrong wallet password and an unknown alias.
- **ADB-REQ-07 In-Memory**: the In-Memory column store on ADB-Free is either enabled, with population of `product`, `response_cache`, `embedding_cache`, and `chat_route` verified in `V$IM_SEGMENTS`, or the reason it cannot be enabled is documented and pinned by an acceptance test.
- **ADB-REQ-08 Select AI**: `manage.py database select-ai setup|ask` creates `GEMINI_CRED` and `COFFEE_GEMINI` for the app schema and runs `DBMS_CLOUD_AI.GENERATE`. Acceptance proves the prerequisites without a key and `showsql` with a key.
- **ADB-REQ-09 Integration test strategy**: per D3, the ephemeral container requests the free flavor, and ADB tests skip with a reason unless `ORACLE_ADB_ACCEPTANCE=1`.
- **ADB-REQ-10 Documentation and knowledge**: README, AGENTS, docs pages, migrations README, MCP doc, GCE lab, knowledge chapters, presentation facts, and test catalogs describe the ADB-Free default, the free flavor, wallet use, vector memory, In-Memory, and Select AI accurately, and `make docs` builds without warnings.
- **ADB-REQ-11 APEX pause**: the APEX specs are marked paused in the specs index, and the installer code stays untouched behind the free flavor.

### Requirement-to-Task Traceability

| Requirement | Tasks | Verification strategy | Primary files | Primary tests |
| --- | --- | --- | --- | --- |
| ADB-REQ-01 | 1.1, 1.3 | behavior_tdd | `tools/oracle/database.py`, `Makefile` | `src/tests/unit/tools/test_oracle_database.py`, `src/tests/unit/tools/test_oracle_cli.py` |
| ADB-REQ-02 | 1.1 | behavior_tdd | `tools/oracle/adb.py` | `src/tests/unit/tools/test_oracle_database.py` |
| ADB-REQ-03 | 1.2 | behavior_tdd | `tools/oracle/adb.py`, `tools/oracle/database.py` | `src/tests/unit/tools/test_oracle_adb.py` |
| ADB-REQ-04 | 1.3 | behavior_tdd | `tools/oracle/cli/database.py`, `tools/oracle/cli/apex.py`, `tools/oracle/cli/ords.py`, `Makefile` | `src/tests/unit/tools/test_oracle_cli.py` |
| ADB-REQ-05 | 1.4 | behavior_tdd | `tools/lib/utils.py`, `tools/oracle/connection.py`, `tools/cli/doctor.py`, `tools/cli/init.py` | `src/tests/unit/tools/test_managed_env.py` |
| ADB-REQ-06 | 2.1 | integration_acceptance | `src/tests/fixtures/adb.py`, `Makefile`, `pyproject.toml` | `src/tests/integration/db/test_adb_free.py` |
| ADB-REQ-07 | 2.2 | integration_acceptance | `.agents/bundles/knowledge/gotchas/oracle-sqlspec-and-queues.md` | `src/tests/integration/db/test_adb_free.py` |
| ADB-REQ-08 | 1.2 (ACL and grant), 2.3 | behavior_tdd | `tools/oracle/select_ai.py`, `tools/oracle/cli/select_ai.py`, `manage.py` | `src/tests/unit/tools/test_oracle_select_ai.py`, `src/tests/integration/db/test_adb_free.py` |
| ADB-REQ-09 | 1.1, 2.1 | behavior_tdd, integration_acceptance | `src/tests/integration/conftest.py`, `src/tests/fixtures/adb.py` | `src/tests/integration/db/test_sqlspec_connection.py`, `src/tests/integration/db/test_adb_free.py` |
| ADB-REQ-10 | 3.1 (catalog rows in 1.1-2.3) | documentation_validation | `README.md`, `docs/**`, `.agents/bundles/knowledge/**` | `make docs`, `src/tests/unit/test_okf_layout.py` |
| ADB-REQ-11 | 1.3, 3.1 | behavior_tdd, documentation_validation | `tools/oracle/cli/apex.py`, `tools/oracle/cli/ords.py`, `.agents/bundles/specs/index.md` | `src/tests/unit/tools/test_oracle_cli.py` |

### Global Constraints

- Python in `src/` and `tools/`: no inline `#` comments (directive pragmas only), Google docstrings, PEP 604/585 types, a module docstring and `__all__` in new modules, and top-level imports in new modules (`tools/oracle/adb.py`, `tools/oracle/select_ai.py`, `tools/oracle/cli/select_ai.py`). Existing lazy imports in `tools/oracle/cli/*` may stay. Remove inline comments from any `tools/` module a task rewrites.
- Tests follow `src/tests/AGENTS.md`: 5-section layout, a docstring on every test, no `class Test*`, no `unittest.mock` under `integration/` or `fixtures/`, no new `conftest.py`, and flat tool tests under `src/tests/unit/tools/`.
- The ADB path never uses SYSDBA, `sqlplus / as sysdba`, or SPFILE changes. ADMIN is the ceiling.
- Never print, log, or embed passwords or API keys; bind secrets as SQL parameters; the wallet stays in gitignored `.envs/`.
- `DatabaseSettings.get_queue_config()` stays a separate pool with `session_key="queue_db_session"`; the app pool keeps `enable_AutoLob=True`.
- Coordinate privacy and controller security rules stay untouched.
- Every task closes with `make lint` and `make test-unit` green and one signed, local, conventional commit that stages only task paths. `.env` is never committed.
- Live steps need Docker or rootful Podman with 4 CPUs and 8 GiB for ADB-Free, plus about 2 GiB for the ephemeral gvenzl test container.

### Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| ADB-Free lacks the elastic vector pool, so HNSW DDL fails with ORA-51962 | Low-Medium | High | June ADB-Free ran the HNSW migrations; Task 1.2 runs `coffee upgrade` live; on failure, record it and `/flow:revise` (IVF indexes are the fallback candidate). |
| Rootless Podman cannot mount OFS with `/dev/fuse` | Medium | High | Document Docker or rootful Podman; doctor reports the runtime. |
| Host lacks 4 CPUs and 8 GiB, or runs ADB plus the test container | Medium | Medium | Doctor warnings; docs state the totals. |
| Legacy `oracle-free-db` holds port 1521 | High on existing checkouts | Medium | Preflight refusal with removal commands. |
| `latest-26ai` drifts or the Oracle registry lags GHCR | Medium | Medium | Record the digest; pin with `ORACLE_IMAGE` or switch to GHCR. |
| Container egress or a missing key blocks Select AI | Medium | Medium | ACL provisioning; document `DBMS_CLOUD_CONTAINER_ADMIN.set_database_property('HTTP_PROXY', ...)`; key-gated test. |
| `--recreate` with a reattached `/u01/data` does not reuse data | Medium | Medium | Task 1.1 live check with a decided fallback (recreate drops the volume). |
| Host 1521 maps to container 1522, so walletless TLS may demand a client certificate (research C1) | Medium | Low | Task 2.1 asserts the observed behavior with both branches defined. |

## Implementation Plan

### Phase 1: Managed ADB-Free database

- [ ] Task 1.1: Run ADB-Free 26ai as the default managed container and export its mTLS wallet
- [ ] Task 1.2: Provision the app schema as ADMIN over the wallet with Select AI prerequisites
- [ ] Task 1.3: Route infra CLI and Makefile by flavor and refuse APEX/ORDS lifecycle on ADB-Free
- [ ] Task 1.4: Generate the managed wallet environment, explicit deployment mode, doctor checks, and SQLcl wallet connection

Phase 1 gate (`checkpoint.phase`): `make lint`, `make test-unit`, and `make test-integration` green; live `make start-infra`, `uv run python manage.py database connect test`, and `uv run coffee upgrade` against ADB-Free.

### Phase 2: Runtime verification on ADB-Free

- [ ] Task 2.1: Add the opt-in ADB-Free acceptance suite for wallet pools, indexes, vector memory, and TLS
- [ ] Task 2.2: Probe the In-Memory column store on ADB-Free and enable or document population
- [ ] Task 2.3: Add Select AI setup and ask commands with live acceptance

Phase 2 gate: `make test-adb` green with and without `SELECT_AI_GEMINI_API_KEY`; `make test` green.

### Phase 3: Documentation and knowledge

- [ ] Task 3.1: Align README, docs, knowledge, presentation facts, and the specs index with the ADB-Free default

Phase 3 gate: `make docs`, `make lint`, `make test`, `make test-adb`; live `uv run coffee run` with `curl -fsS http://localhost:5006/health`, `/explore` rendering, and `curl -kfsS -o /dev/null https://localhost:8443/ords/sql-developer`.

## Continuity Snapshot

- **Active Flow / Lifecycle**: `adb-free-swap` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**: D1-D13 above; D2, D3, D11, and D12 await user confirmation at the planning gate.
- **Newest Discoveries**:
  1. Oracle's README now documents `ghcr.io/oracle/adb-free:latest-26ai` = `26.9.4.1-26ai` (multi-arch, 4 CPUs, 8 GiB) and a `/u01/data` volume.
  2. June's `configure_vector_memory()` relied on `sqlplus / as sysdba`, which ADB-Free denies (ORA-01017); Autonomous AI Database manages the vector pool elastically.
  3. `src/tests/unit/test_test_suite_guards.py` bans `src/tests/unit/tools/oracle/`, so tool tests stay flat under `src/tests/unit/tools/`.
  4. `tools/deploy/terraform/db_vm.tf` reads the gvenzl hook SQL files, so those files stay.
  5. CI runs unit tests only; integration suites run locally.
- **Blockers & Unblock Conditions**: none.
- **Next Exact Step**: approve the plan, then claim Task `1.1` (`tasks/1.1.md`).
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `research/adb-free-evidence.md`
  - `.agents/bundles/knowledge/patterns/operations.md`
  - `.agents/bundles/knowledge/gotchas/oracle-sqlspec-and-queues.md`
  - `src/tests/AGENTS.md`, `src/tests/unit/AGENTS.md`, `src/tests/integration/AGENTS.md`

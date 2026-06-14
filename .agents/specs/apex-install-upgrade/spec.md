# Flow Spec: apex-install-upgrade (Chapter 2)

*Beads: `oracledb-vertexai-apxg.2` (chapter epic)*
*Parent PRD: [../apex-gvenzl-install/prd.md](../apex-gvenzl-install/prd.md)*
*Depends on: Ch1 `apex-media-staging` (staged media + `ApexMedia.ensure()` / `paths()`)*
*Status: Implementation-ready (refreshed 2026-06-14 against the landed gvenzl `database.py`)*

---

## 1.0 Context

The gvenzl revert has **landed** (`tools/oracle/database.py` HEAD = `gvenzl/oracle-free:latest`). gvenzl
permits SYSDBA OS-auth inside the container (`sqlplus / as sysdba`), which the `adb-free` image denied
(SYS locked, `ORA-01017`). This chapter consumes Ch1's staged media and delivers an **idempotent
install/upgrade engine** plus the `manage.py infra apex` command surface.

**This spec was rewritten against the real gvenzl contract** (the original draft assumed the now-removed
`adb-free` API):

| Assumed (adb-free draft) | Reality (gvenzl, HEAD) |
|---|---|
| `OracleDatabase._exec_sysdba_sql(...)` | **Removed.** Only `exec_sql(sql, *, user=None)` exists, running as the **app user** (not SYSDBA). |
| SYSDBA available via that helper | gvenzl OS-auth: `sqlplus / as sysdba` works **inside the container** (connects to `CDB$ROOT`; `ALTER SESSION SET CONTAINER=FREEPDB1` for the PDB). |
| Media via `_build_run_command()` bind-mount | **`docker cp`** the staged `apex/` tree into the container (no `database.py` edit). |
| Auto-install in `OracleDatabase.start()` | Auto-install in **`cli/database.py::_database_start()`** (the `infra start` CLI), keeping the lifecycle class untouched. |
| Service name `FREEPDB1` (assumed) | `PDB_SERVICE_NAME = "freepdb1"`; container `oracle-free-db`; port `1521`. |

**SYSDBA mechanism (locked with user):** installer-owned `docker exec … sqlplus / as sysdba` via the
existing `ContainerRuntime`. `database.py` stays essentially untouched.

---

## 2.0 Requirements

- Detect the installed APEX version (`APEX_RELEASE.version`) in `FREEPDB1` and decide skip / install /
  upgrade. Absent APEX (view missing → `ORA-00942`) reads as "not installed".
- Stage Ch1 media **into** the running container via `docker cp` (idempotent; re-copy on `--force`).
- Install/upgrade into `FREEPDB1` via container SYSDBA, each step `ALTER SESSION SET CONTAINER=FREEPDB1`
  first: `apexins.sql SYSAUX SYSAUX TEMP /i/`, then REST config + instance-admin + workspace via
  **non-interactive PL/SQL** (`apex_instance_admin` / `apex_util`) rather than the interactive
  `apxchpwd.sql` / `apex_rest_config.sql` prompts.
- Provision the **COFFEE** workspace + **ADMIN** developer user idempotently (logic ported from the
  removed `tools/oracle/on_init/02_create_apex_workspace.sh`, recoverable from git history), keyed on
  `apex_workspaces`.
- Expose `manage.py infra apex install | upgrade | status`; auto-install on `infra start` when APEX is
  absent (with `--skip-apex` to opt out for fast iterations).
- Fully idempotent: re-running install is a no-op; `upgrade --apex-version <newer>` upgrades in place.
- Fail loudly if `apex_release` does not report the target version after install.

---

## 3.0 Proposed Changes

### Component: APEX install engine (`tools/oracle/`)

#### [CREATE] `tools/oracle/apex_install.py`
- `@dataclass ApexInstallConfig`: `pdb: str = "FREEPDB1"`, `container_apex_dir: str = "/tmp/apex"`,
  `images_url_path: str = "/i/"`, `admin_user: str = "ADMIN"`, `admin_password` (demo default / env),
  `workspace: str = "COFFEE"`, `primary_schema` (from `DATABASE_USER`, default `app`). `from_env()`.
- `class ApexInstaller`:
  - `__init__(self, runtime: ContainerRuntime, db: OracleDatabase, media: ApexMedia,
    config: ApexInstallConfig | None = None, console: Console | None = None)`.
  - `_exec_sysdba(sql: str) -> str` — `runtime.run_command(["exec", container, "bash", "-c",
    f"sqlplus -S -L / as sysdba <<'SQL'\n{preamble}{sql}\nexit\nSQL"])` where `preamble` is
    `ALTER SESSION SET CONTAINER={pdb};\nWHENEVER SQLERROR EXIT SQL.SQLCODE;\n`. Raises `ApexInstallError`
    on non-zero / `ORA-` in output (except tolerated ones for detection).
  - `_run_script(in_container_path, args)` — SYSDBA `@<path> <args...>` from `container_apex_dir`.
  - `installed_version() -> str | None` — `SELECT version FROM apex_release;` (heading/feedback off);
    parse; `None` when the view is absent (`ORA-00942`).
  - `stage_media(*, force=False)` — `media.ensure(force=force)`, then `run_command(["exec", container,
    "mkdir", "-p", container_apex_dir])` + `run_command(["cp", f"{paths.apex_dir}/.",
    f"{container}:{container_apex_dir}"])`.
  - `install(*, force=False) -> str` — idempotent: skip if installed `== target` and not force; else
    `stage_media` → `_run_script("apexins.sql", ["SYSAUX","SYSAUX","TEMP","/i/"])` → REST/admin PL/SQL →
    `provision_workspace()`; verify `installed_version() == target`; returns the version.
  - `provision_workspace()` — idempotent PL/SQL: `apex_instance_admin.add_workspace` (COFFEE → primary
    schema) + `apex_util.create_user` (ADMIN dev user), guarded on `apex_workspaces`.

### Component: infra apex CLI (`tools/oracle/cli/`)

#### [CREATE] `tools/oracle/cli/apex.py`
- `apex_group` with `install` (`--apex-version`, `--force`, `--english/--full`), `upgrade`
  (`--apex-version`), `status` (prints installed vs target). Each builds `ApexMedia` (Ch1) +
  `OracleDatabase` + `ApexInstaller` and runs idempotently. (Ch4 adds `export`/`import` here.)

#### [MODIFY] `tools/oracle/cli/database.py`
- `database_start` / `_database_start()` — add `--skip-apex`; after `db.start()`, when not skipped and
  `installed_version()` is `None`, run `ApexInstaller(...).install()`. (Lifecycle class `database.py`
  untouched.)

#### [MODIFY] `tools/oracle/cli/__init__.py` + `tools/oracle/__init__.py`
- Export `apex_group` (add to imports + `__all__`).

#### [MODIFY] `manage.py`
- `from tools.oracle import apex_group`; `infra_group.add_command(apex_group, name="apex")` so
  `uv run python manage.py infra apex …` resolves (kept off `coffee`).

> **No `tools/oracle/database.py` change.** Media enters via `docker cp`; SYSDBA via `docker exec`;
> auto-install at the CLI layer. This is the "minimal database.py contact" path chosen with the user.

---

## 4.0 Implementation Plan (TDD)

- [ ] **Task 2.1** — `ApexInstallConfig` + `_exec_sysdba()` + `installed_version()` (+ version compare).
  Unit tests mock `ContainerRuntime.run_command` output (APEX absent → `ORA-00942` → None; `24.2.14`;
  `26.1`) and assert the `exec … sqlplus / as sysdba` argv + `ALTER SESSION SET CONTAINER=FREEPDB1`.
- [ ] **Task 2.2** — `install()` idempotent orchestration (`apexins` + REST/admin PL/SQL),
  skip/install/upgrade logic, post-verify `== target`. Unit tests assert the exec sequence + skip path
  (installed == target → no exec) + fail-loud when post-verify mismatches.
- [ ] **Task 2.3** — `provision_workspace()` (COFFEE + ADMIN dev user, ported from git history)
  idempotent on `apex_workspaces`. Unit tests for create vs already-exists (mock run_command).
- [ ] **Task 2.4** — `stage_media()` (`docker cp`) + `cli/database.py` auto-install-on-start with
  `--skip-apex`. Unit tests: `cp` argv shape; install invoked only when `installed_version()` is None;
  `--skip-apex` skips. (No `database.py` edit.)
- [ ] **Task 2.5** — `tools/oracle/cli/apex.py` `install|upgrade|status` + `__init__`/`manage.py` wiring.
  Unit tests via Click `CliRunner` (mock `ApexInstaller`); assert `manage.py infra apex` resolves.

---

## 5.0 Verification Plan

### Automated
```bash
uv run pytest src/tests/unit/tools/oracle/test_apex_install.py
uv run ruff check tools/oracle/apex_install.py tools/oracle/cli/apex.py
```
- Deterministic: `ContainerRuntime.run_command` mocked; no real DB/container.

### Manual (real, after `make start-infra`)
```bash
uv run python manage.py infra apex install --apex-version 26.1
uv run python manage.py infra apex status   # -> installed: 26.1.x (target 26.1)
uv run python manage.py database connect test
```
- `SELECT version FROM apex_release;` (in `FREEPDB1`) returns `26.1.x`; COFFEE workspace + ADMIN exist.

---

## 6.0 Definition of Done

- `infra apex install` installs APEX 26.1 into `FREEPDB1` idempotently via container SYSDBA; `status`
  reports it; `upgrade` re-runs cleanly to a newer version.
- COFFEE workspace + ADMIN dev user provisioned; `infra start` auto-installs when absent (`--skip-apex`
  opts out).
- Post-install verification asserts `apex_release == target` (fails loudly otherwise).
- `tools/oracle/database.py` (the lifecycle class) is **not** modified; `ruff` + the new unit tests pass.

---

## Open Questions (carried)
- Exact non-interactive PL/SQL for the instance-admin password (`apex_instance_admin.set_parameter`
  vs a scripted `apxchpwd`); confirm against APEX 26.1 during Task 2.2.
- REST/listener user setup: `apex_rest_config_core.sql` with bind args vs pure `apex_instance_admin`
  PL/SQL — pick the non-interactive path that 26.1 supports (validate in Task 2.2).

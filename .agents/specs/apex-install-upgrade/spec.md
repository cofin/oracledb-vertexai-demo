# Flow Spec: apex-install-upgrade (Chapter 2)

*Beads: `oracledb-vertexai-apxg.2` (chapter epic)*
*Parent PRD: [../apex-gvenzl-install/prd.md](../apex-gvenzl-install/prd.md)*
*Depends on: Ch1 `apex-media-staging` (staged media + `container_mounts()` contract)*
*Status: Implementation-ready*

---

## 1.0 Context

`gvenzl/oracle-free` permits `sqlplus / as sysdba`, so APEX installs/upgrades via the standard
`apexins.sql` path against `FREEPDB1` — the capability the `adb-free` image denied (SYS locked,
`ORA-01017`). This chapter consumes the staged media from Ch1 and delivers an **idempotent install/upgrade
engine** plus the `manage.py infra apex` command surface, auto-running install on `infra start` when APEX
is absent. It ports the workspace/dev-user provisioning that lived in the removed
`tools/oracle/on_init/02_create_apex_workspace.sh`.

---

## 2.0 Requirements

- Detect the installed APEX version (`APEX_RELEASE.version_no`) and decide skip / install / upgrade.
- Install/upgrade into `FREEPDB1` via container SYSDBA: `apexins.sql SYSAUX SYSAUX TEMP /i/`, then
  `apex_rest_config.sql` (REST/listener users for ORDS), then `apxchpwd.sql` (instance admin password).
- Provision the **COFFEE** workspace + **ADMIN** developer user idempotently (ported from the removed
  script), keyed on `apex_workspaces`.
- Make staged APEX media available *inside* the container at install time (bind-mount via Ch1's
  `container_mounts()`), so `apexins.sql` runs from a real in-container path.
- Expose `manage.py infra apex install | upgrade | status`; auto-install on `infra start` when missing.
- Fully idempotent: re-running install is a no-op; `upgrade --apex-version <newer>` upgrades in place.
- Fail loudly if `apex_release` does not report the target version after install.

---

## 3.0 Proposed Changes

### Component: APEX install engine (`tools/oracle/`)

#### [CREATE] `tools/oracle/apex_install.py`
- `@dataclass ApexInstallConfig`: `pdb: str = "FREEPDB1"`, `images_path: str = "/i/"`,
  `admin_user: str = "ADMIN"`, `admin_password` (from env/demo default), `workspace: str = "COFFEE"`,
  `primary_schema` (from `DATABASE_USER`, default `app`).
- `class ApexInstaller(runtime, db: OracleDatabase, media: ApexMedia, config)`:
  - `installed_version() -> str | None` — query `APEX_RELEASE` via `db._exec_sysdba_sql` /
    `ALTER SESSION SET CONTAINER=FREEPDB1`; `None` when APEX absent.
  - `install(*, force=False) -> str` — idempotent: skip if installed `== target`; run `apexins` if absent
    or installed `< target` (upgrade); returns the resulting version. Verifies `apex_release` == target.
  - `_run_apexins()`, `_run_rest_config()`, `_run_chpwd()` — `sqlplus / as sysdba` execs from the mounted
    `apex/` dir, `ALTER SESSION SET CONTAINER=FREEPDB1` first.
  - `provision_workspace()` — idempotent COFFEE workspace + ADMIN dev user via
    `apex_instance_admin.add_workspace` + `apex_util.create_user`, guarded on `apex_workspaces`.
- Reuse `tools/oracle/database.py::_exec_sysdba_sql` (SYSDBA exec) and Ch1 `ApexMedia.paths()`.

#### [MODIFY] `tools/oracle/database.py`
- `_build_run_command()` — add the APEX bind-mount from `ApexMedia.container_mounts(db_target="/opt/oracle/apex")`
  so `apex/` (incl. `images/`) is present in the gvenzl container.
- `start()` — after `wait_for_healthy()` / `configure_vector_memory()`, call `ApexInstaller.install()` +
  `provision_workspace()` when `installed_version()` is `None` (auto-install on first start), idempotent.

### Component: infra apex CLI (`tools/oracle/cli/`)

#### [CREATE] `tools/oracle/cli/apex.py`
- `apex_group` with `install` (`--apex-version`, `--force`), `upgrade` (`--apex-version`), `status`
  (prints installed vs target). Each builds `ApexMedia` (Ch1) + `ApexInstaller` and runs idempotently.
  (Ch4 adds `export`/`import` to this same group.)

#### [MODIFY] `manage.py`
- Register `apex_group` under the `infra` group (alongside the `database` lifecycle commands) so
  `uv run python manage.py infra apex …` resolves. Keep it off `coffee` (maintainer surface).

---

## 4.0 Implementation Plan (TDD)

- [ ] **Task 2.1** — `ApexInstallConfig` + `installed_version()` (APEX_RELEASE via SYSDBA exec) + version
  compare. Unit tests mock `_exec_sysdba_sql` output (absent, 24.2.14, 26.1).
- [ ] **Task 2.2** — `install()` idempotent orchestration (`apexins`/`apex_rest_config`/`apxchpwd`),
  skip/install/upgrade logic, post-verify == target. Unit tests assert the exec sequence + skip path.
- [ ] **Task 2.3** — `provision_workspace()` (COFFEE + ADMIN dev user, ported) idempotent on
  `apex_workspaces`. Unit tests for create vs already-exists.
- [ ] **Task 2.4** — `database.py`: APEX bind-mount via Ch1 `container_mounts()` + auto-install-on-start
  when APEX missing. Unit tests assert mount in run command + install invoked only when absent.
- [ ] **Task 2.5** — `tools/oracle/cli/apex.py` `install|upgrade|status` + `manage.py infra` wiring.
  Unit tests via Click runner (mock `ApexInstaller`).

---

## 5.0 Verification Plan

### Automated
```bash
uv run pytest src/tests/unit/tools/oracle/test_apex_install.py
make lint
```
- Deterministic: container/SYSDBA exec mocked; no real DB.

### Manual (real, after gvenzl revert + Ch1)
```bash
uv run python manage.py infra apex install --apex-version 26.1
uv run python manage.py infra apex status   # -> installed: 26.1.x (target 26.1)
```
- `SELECT version_no FROM apex_release;` returns `26.1.x`; COFFEE workspace + ADMIN user exist.

---

## 6.0 Definition of Done

- `infra apex install` installs APEX 26.1 into `FREEPDB1` idempotently; `status` reports it; `upgrade`
  re-runs cleanly to a newer version.
- COFFEE workspace + ADMIN dev user provisioned; auto-install fires on a fresh `infra start`.
- Post-install verification asserts `apex_release == target` (fails loudly otherwise).
- `make lint` and the new unit tests pass.

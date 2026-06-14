# Master PRD: APEX 26.1 Install/Upgrade for gvenzl + APEXlang Source

*PRD ID: `apex-gvenzl-install`*
*Beads: `oracledb-vertexai-apxg` (master epic)*
*Research: [../../research/research_apex_upgrade/](../../research/research_apex_upgrade/)*
*Created: 2026-06-14*
*Status: Draft — all 5 chapters specced & implementation-ready (25 Beads tasks)*

---

## North Star

Install and upgrade **Oracle APEX 26.1** (with ORDS) into the **`gvenzl/oracle-free`** development
container, drive it entirely through the existing **`manage.py infra`** management surface, and adopt
**APEXlang** as the application source-of-truth under **`src/apex/`**. This unblocks the APEXlang KScope
demo, which the `adb-free` image cannot deliver.

**Why this exists (validated 2026-06-14):** the `adb-free:latest-26ai` container ships **APEX 24.2.14**,
locks **SYS** (`ORA-01017`), exposes **no `adb-cli` upgrade verb**, and has **no in-container upgrade
path** (Oracle docs: "no automatic patching… check the repository for newer versions"). The only ADB
upgrade mechanism (cloud "apply/defer APEX update") does not exist in the free container. By contrast,
`gvenzl/oracle-free` permits `sqlplus / as sysdba`, so the standard `apexins.sql` install/upgrade works,
and the APEX 26.1 zip is a **public, no-login download**. Full validation:
`.agents/research/research_apex_upgrade/research.md`.

---

## Scope

**In scope:** infra to install/upgrade APEX 26.1 + ORDS in gvenzl; the `manage.py infra apex` command
group; the COFFEE workspace + dev user provisioning; the `src/apex/` APEXlang layout and SQLcl
export/import commands; tests and docs.

**Out of scope:** authoring an actual Cymbal Coffee APEX application (separate follow-on); `lab.md` and
UI quality work (owned by the concurrent `adb-podman-lab-hardening` / `research_adb_hooks_ux_lab`
effort); the container *base* revert itself (a separate agent is reverting adb-free → gvenzl — this PRD
is a **precondition consumer**, not the owner of that revert).

---

## Locked Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Deliverable scope | **Infra + APEXlang tooling** (no app authoring) | Unblocks everything; app can be built interactively later |
| Install method | **Runtime management command** (`manage.py infra apex …`), SYSDBA `apexins`, idempotent, auto-run on `infra start` when APEX missing | No image build; "upgrade" = re-run; controllable |
| ORDS runtime | **Sidecar launched by the Python CLI** (official `database/ords` image) | Matches prod topology; honors "CLI owns infra, not compose" |
| Version pinning | **Parameterized `--apex-version`, default `26.1`**, per-version host cache | Same command serves future upgrades |

---

## Reviewed Sources

- **`tools/oracle/database.py`** (branch) — `adb-free` config; `_exec_sysdba_sql()` (`:467`) assumes SYS
  (false on adb-free); `initialize_db_users()` (`:478`) ADMIN-via-wallet pattern. The gvenzl base
  (image `gvenzl/oracle-free:latest`, port 1521, `/container-entrypoint-initdb.d` + `-startdb.d` hook
  mounts) is being restored by the concurrent revert (see `git show main:tools/oracle/database.py`).
- **`tools/oracle/cli/database.py`** (`:42–176`) — `infra` lifecycle command group (start/stop/restart/
  remove/logs/status); the home for new `infra apex` verbs.
- **`tools/oracle/cli/sqlcl.py`** + **`tools/oracle/sqlcl_installer.py`** — SQLcl already integrated
  (install/verify/uninstall); reused for APEXlang export/import.
- **`manage.py`** (`:74–90`, `:98–109`) — `infra` and `database` command groups.
- **Removed `tools/oracle/on_init/02_create_apex_workspace.sh`** — APEX `COFFEE` workspace +
  `apex_util.create_user` logic to port into the install engine.
- **`research_apex_upgrade/research.md`** — version/SYS/upgrade-path validation; APEXlang export
  structure and SQLcl command.

---

## Roadmap

### Chapter 1 — `apex-media-staging` (`oracledb-vertexai-apxg.1`)
Acquire and stage APEX media for the container. Version-parameterized download of `apex_<ver>.zip` from
the public OTN URL (default 26.1), integrity verification, per-version host cache, extraction, and a
defined staging layout/mount points consumed by Ch2 (install) and Ch3 (ORDS `/i/` images).
**Status: implementation-ready (spec drafted).**

### Chapter 2 — `apex-install-upgrade` (`oracledb-vertexai-apxg.2`)
Idempotent install/upgrade engine: `apexins.sql` / `apex_rest_config.sql` / `apxchpwd.sql` via container
SYSDBA into `FREEPDB1`; `APEX_RELEASE` detection to skip-or-upgrade; instance-admin password; COFFEE
workspace + dev user provisioning (ported from the removed script). Command surface `manage.py infra apex
install|upgrade|status`; auto-install hook on `infra start` when APEX is absent.

### Chapter 3 — `apex-ords-sidecar` (`oracledb-vertexai-apxg.3`)
ORDS sidecar lifecycle launched by the Python CLI: connect to gvenzl `FREEPDB1`, serve `/ords` and APEX
static images at `/i/` from staged `apex/images`, expose HTTPS/HTTP, health-check, and integrate into
`infra start/stop/remove/status`. Pin a compatible ORDS↔APEX pairing.

### Chapter 4 — `apexlang-source` (`oracledb-vertexai-apxg.4`)
Define `src/apex/<alias>/` (`application.apx`, `pages/`, `shared-components/`, `supporting-objects/`,
`deployments/`, `.apex/`). Add `manage.py infra apex export|import` wrapping SQLcl
`apex export -applicationid <id> -exptype apexlang -dir src/apex/<alias>` (+ import), reusing the SQLcl
integration. Verify a full-app round-trip on APEX 26.1.

### Chapter 5 — `apex-verify-docs` (`oracledb-vertexai-apxg.5`)
Unit/integration tests (mocked SYSDBA/container exec + a real smoke path: install → workspace → ORDS →
`apex_release=26.1` → export round-trip). Align env/settings for the gvenzl revert (ports, `FREEPDB1`,
no wallet/mTLS). Update `quickstart` / `architecture` / `oracle-vector-search` guides + `CLAUDE.md`.
Excludes `lab.md`.

---

## Global Constraints

- **Precondition coordination:** the container base revert (adb-free → gvenzl) is owned by a separate
  agent and standalone task `oracledb-vertexai-2q0`. Ch1/Ch2 must build on the restored gvenzl base; do
  not re-implement the revert here.
- **CLI owns infra, not compose:** ORDS sidecar is launched via the Python CLI (`docker run`), matching
  the project rule; `compose.yaml` stays opt-in only.
- **No backwards-compat shims:** remove adb-free-specific APEX assumptions outright; do not leave dual
  adb-free/gvenzl branches behind feature flags.
- **TDD + aggregate gates:** `make lint` and `make test` must pass; new lifecycle code carries
  deterministic unit tests (mock container/SYSDBA exec) plus a documented real smoke path.
- **Floor-only dependency pins; SPDX headers; docstrings describe behavior only** (project conventions).
- **Idempotency everywhere:** every `apex`/ORDS command is safe to re-run.

---

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| APEX install (`apexins.sql`) is long (~minutes) → slow first `infra start` | Idempotent + cached media; run once; clear progress output; allow `--skip-apex` for fast iterations |
| ORDS↔APEX version mismatch breaks `/i/` images or `/ords/apex` | Pin a known-good ORDS image tag against APEX 26.1; smoke-check `apex_release` + a page render in Ch5 |
| OTN URL/format changes or `_en` vs full zip differences | Parameterize URL + filename; verify `apexins.sql` presence post-extract; default to the English zip, allow full |
| Revert coordination drift (ports/service/hooks) with the other agent | Treat gvenzl base as a precondition; Ch5 owns the settings/env alignment; coordinate via `apxg` notes + `2q0` |
| SYSDBA bounce / restart races container supervisor (as seen on adb-free) | gvenzl runs SYSDBA OS-auth natively; prefer init-hook/`sqlplus / as sysdba` exec over in-session shutdown |
| Demo data loss when recreating the container for a clean install | Re-derive from committed fixtures via `coffee upgrade`; never depend on container-internal state |

---

## Acceptance Criteria

- `uv run python manage.py infra apex install` (or auto-on-start) installs APEX **26.1** into `FREEPDB1`
  in the gvenzl container; `SELECT version_no FROM apex_release` returns `26.1.x`.
- ORDS sidecar serves `https://localhost:<port>/ords/apex` (login page renders) with images at `/i/`.
- The COFFEE workspace + dev user exist after install (ported provisioning).
- `manage.py infra apex upgrade --apex-version <newer>` upgrades in place, idempotently.
- `manage.py infra apex export --app-id <id>` writes a diffable APEXlang tree under
  `src/apex/<alias>/`; `import` round-trips it back on APEX 26.1.
- `make lint` and `make test` pass; the documented smoke path succeeds end-to-end.

---

## Open Questions (carry into chapters)

1. Default to the **English** APEX zip (`apex_26.1_en.zip`, ~257 MB) or the **full** zip
   (`apex_26.1.zip`, ~326 MB)? (Recommend English for the demo; allow full via flag.)
2. Which **ORDS image tag** pairs cleanly with APEX 26.1 for the sidecar? (Validate in Ch3.)
3. Final **container mount layout** for the `apex/` tree and images — confirm against the reverted gvenzl
   `_build_run_command()` once the revert lands.
4. Canonical **app alias/ID** for `src/apex/<alias>/` (needed in Ch4; depends on the future demo app).

---

## Next Step

Chapter 1 (`apex-media-staging`) is implementation-ready. Run **`/flow:implement`** to begin, or
**`/flow:plan`** to draft specs for Chapters 2–5.

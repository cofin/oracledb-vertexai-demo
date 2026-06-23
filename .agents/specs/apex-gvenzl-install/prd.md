# Master PRD: APEX 26.1 Install/Upgrade for gvenzl + APEXlang Source

*PRD ID: `apex-gvenzl-install`*
*Beads: `oracledb-vertexai-apxg` (master epic)*
*Research: [../../research/research_apex_upgrade/](../../research/research_apex_upgrade/)*
*Created: 2026-06-14*
*Status: Reconciled — Ch1-Ch4 completed or absorbed by the active APEX ops roadmap; Ch5 settings/unit gates verified and smoke/docs/final work deferred to `apex-demo-verification-docs`.*

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
| Install method | **`manage.py infra apex …`** runtime command; **installer-owned `docker exec … sqlplus / as sysdba`** (gvenzl OS-auth), media staged into the container via **`docker cp`**, idempotent, auto-run from `cli/database.py` on `infra start` when APEX missing (`--skip-apex` opts out) | No image build; "upgrade" = re-run; **keeps `database.py` untouched** (revert-safe) |
| ORDS runtime | **Sidecar launched by the Python CLI** (official `database/ords` image) | Matches prod topology; honors "CLI owns infra, not compose" |
| Version pinning | **Parameterized `--apex-version`, default `26.1`**, per-version host cache | Same command serves future upgrades |

---

## Reviewed Sources

- **`tools/oracle/database.py`** (HEAD, gvenzl — **revert landed 2026-06-14**) — `DEFAULT_IMAGE =
  gvenzl/oracle-free:latest`, `PDB_SERVICE_NAME = "freepdb1"`, container `oracle-free-db`, port 1521.
  `OracleDatabase(runtime, config, console)`; `exec_sql(sql, *, user=None)` runs as the **app user**
  (no SYSDBA helper — `_exec_sysdba_sql` was removed). `_build_run_command()` mounts `on_init` →
  `/container-entrypoint-initdb.d` and `on_startup` → `/container-entrypoint-startdb.d` (run as SYSDBA).
  SYSDBA for APEX = installer-owned `docker exec … sqlplus / as sysdba` (OS-auth); the lifecycle class
  is **not** modified by this PRD.
- **`tools/oracle/container.py`** — `ContainerRuntime.run_command(args, *, capture_output, check,
  timeout)`; generic enough for `["cp", …]` and `["exec", container, "bash", "-c", …]`.
- **`tools/oracle/cli/database.py`** + **`manage.py`** — `infra` is a **flat** group remapping
  `database_group` (start/stop/restart/status/logs/remove→wipe); add `apex` (and later `ords`) as
  subgroups; auto-install hooks into `_database_start()`.
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
**Status: completed and archived locally 2026-06-23.**

### Chapter 2 — `apex-install-upgrade` (`oracledb-vertexai-apxg.2`)
Idempotent install/upgrade engine: `apexins.sql` / `apex_rest_config.sql` / `apxchpwd.sql` via container
SYSDBA into `FREEPDB1`; `APEX_RELEASE` detection to skip-or-upgrade; instance-admin password; COFFEE
workspace + dev user provisioning (ported from the removed script). Command surface `manage.py infra apex
install|upgrade|status`; auto-install hook on `infra start` when APEX is absent.
**Status: completed and archived locally 2026-06-23.**

### Chapter 3 — `apex-ords-sidecar` (`oracledb-vertexai-apxg.3`)
ORDS sidecar lifecycle launched by the Python CLI: connect to gvenzl `FREEPDB1`, serve `/ords` and APEX
static images at `/i/` from staged `apex/images`, expose HTTPS/HTTP, health-check, and integrate into
`infra start/stop/remove/status`. Pin a compatible ORDS↔APEX pairing.
**Status: completed and archived locally 2026-06-23; final standalone CLI task was reconciled into `apex-runtime-hardening`.**

### Chapter 4 — `apexlang-source` (`oracledb-vertexai-apxg.4`)
Absorbed by the post-research `apexlang-lifecycle` chapter on 2026-06-23. The
current source root is `src/apex/<alias>/`; SQLcl 26.1.2 generated this repo's
APEXlang source with hyphenated directories such as `shared-components/` and
`supporting-objects/`. The
local CLI now exposes `manage.py infra apex generate|export|validate|import`
wrapping SQLcl APEXlang commands; live Oracle round-trip verification is carried
by `apex-demo-verification-docs`.

### Chapter 5 — `apex-verify-docs` (`oracledb-vertexai-apxg.5`)
Unit/integration tests (mocked SYSDBA/container exec + a real smoke path: install → workspace → ORDS →
`apex_release=26.1` → export round-trip). Align env/settings for the gvenzl revert (ports, `FREEPDB1`,
no wallet/mTLS). Update `quickstart` / `architecture` / `oracle-vector-search` guides + `CLAUDE.md`.
Excludes `lab.md`.
**Status: reconciled 2026-06-23.** Settings/env and Ch1-Ch4 unit gates are
verified and closed; smoke/docs/final verification are deferred to
`apex-demo-verification-docs` (`oracledb-vertexai-apxo.6`), not completed here.

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
  `src/apex/<alias>/`; `validate` and `import` round-trip it back on APEX 26.1.
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

Chapters 1–3 are complete and archived. Treat the post-research
`apex-ops-console` roadmap as the active source for next implementation work:
`apexlang-lifecycle`, `apex-ops-api`, and `apex-demo-verification-docs` carry
the remaining APEXlang, API, smoke, and docs work.

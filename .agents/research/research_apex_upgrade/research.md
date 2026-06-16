# Research: Upgrading APEX to 26.1 in the ADB Free Container + APEXlang Source at `src/apex/`

**Workspace**: `.agents/research/research_apex_upgrade/`
**Status**: Complete
**Type**: Integration (container/runtime) + New Feature (management command, source layout)
**Date**: 2026-06-14
**Branch**: `feat/inv`
**Validated against**: the live `oracle-free-db` container, `adb-cli`, and authoritative Oracle docs.

> Scope guard: this research covers **APEX version/upgrade** and **APEXlang `src/apex/`** only.
> The concurrent UI / `lab.md` quality work in `research_adb_hooks_ux_lab` is owned by another
> agent and is intentionally out of scope here.

---

## Executive Summary

- **The premise is correct (live-verified).** `container-registry.oracle.com/database/adb-free:latest-26ai`
  ships **Oracle APEX `24.2.14`** (schema `APEX_240200`), **not** APEX 26.1. The just-released
  **APEX 26.1** (GA **2026-05-14**) and its headline **APEXlang** feature are therefore **unavailable**
  on the current container. APEXlang is a 26.1-only feature, so the `src/apex/` goal is hard-blocked
  until APEX is at 26.1.
- **The prior `research_apex_integration` doc is factually wrong on its load-bearing claim.** It asserts
  the `adb-free:latest-26ai` image "has APEX 26.1 … pre-installed." It does not (24.2.14). Two of its
  secondary claims are also false: APEX zips are **not** behind an "SSO wall" (they are public direct
  downloads), and `sqlplus / as sysdba` does **not** work in this container (SYS is locked).
- **In-container APEX upgrade is not supported in `adb-free`.** Confirmed three ways: (1) `adb-cli`
  exposes no apex/ords/upgrade/patch command; (2) Oracle docs state *"There is no automatic patching or
  maintenance windows for the Free Container Image… Check the repository to find newer versions"*; (3)
  the standard manual path (`apexins.sql` as SYS) is impossible because **SYSDBA OS-auth is denied
  (ORA-01017)**, exactly like real Autonomous Database. The cloud ADB self-service "apply/defer APEX
  update" feature **does not exist** in the free container (no fleet-management layer).
- **Two viable paths, and they trade off against the just-completed `adb-free` migration:**
  - **Path A — Image refresh (keeps ADB parity):** an `infra upgrade` command that DataPump-exports the
    app schema, pulls a newer `adb-free` tag, recreates, and re-imports. **But the latest `26ai` image
    still carries APEX 24.2.14** — this only yields 26.1 *if/when Oracle publishes a 26.1-bearing image*,
    on Oracle's schedule, which is **not controllable for a fixed KScope date**.
  - **Path B — SYS-capable base + manual APEX 26.1 (guarantees 26.1 now):** switch the dev DB to
    `container-registry.oracle.com/database/free` (26ai, SYS available) + an ORDS sidecar, and add a
    management command that downloads the public `apex_26.1.zip` and runs `apexins.sql` /
    `apex_rest_config.sql` / `apxchpwd.sql`. Guarantees 26.1 today and is itself a nice "how to upgrade
    APEX" demo — but **reverses** the recent `adb-free` adoption (loses wallet/mTLS parity, Database
    Actions, MongoDB API, the OEE workspace).
- **`src/apex/` is well-defined regardless of path.** APEXlang exports to a diffable tree
  (`application.apx`, `pages/`, `shared-components/`, `supporting-objects/`, `deployments/`, `.apex/`)
  via SQLcl `apex export -applicationid <id> -exptype apexlang`. SQLcl is **already integrated** in this
  repo (`tools/oracle/cli/sqlcl.py`), so `apex export`/`import` management commands are a small add.

---

## Validation Ledger (answers to "validate it's correct")

| Claim under test | Source | Result |
|---|---|---|
| APEX 26.1 is the latest release | Oracle blog "Announcing APEX 26.1 GA"; Release Notes PDF | ✅ True — GA **2026-05-14** |
| APEXlang is real (`.apx`, declarative, source-of-truth) | Oracle "Introducing APEXlang"; SQL Dev VS Code docs | ✅ True — 26.1 feature |
| `adb-free:latest-26ai` "has APEX 26.1 pre-installed" *(prior research)* | **Live container query** | ❌ **False — APEX `24.2.14`** |
| ORDS in the container is current | Live container query | ✅ ORDS `26.1.0.r0791128` |
| DB is 26ai | Live container query | ✅ `Oracle AI Database 26ai … 23.26.2.1.0` |
| APEX download needs Oracle SSO login *(prior research)* | `curl -I` of OTN URL | ❌ **False — public 200, ~326 MB** |
| `sqlplus / as sysdba` works in `adb-free` *(codebase + prior open Q)* | Live `docker exec` | ❌ **False — ORA-01017 (SYS locked)** |
| ADB free container has an APEX upgrade command | Live `adb-cli --help` | ❌ **False — none** |
| Cloud ADB has self-service APEX upgrade | Oracle "apply/defer updates" docs | ✅ True — **but cloud only, not the free container** |

### Evidence captured from the running container (`oracle-free-db`, up 14h, healthy)

```text
# APEX_RELEASE                 -> 24.2.14  (api 2024.11.30)
# DBA_REGISTRY 'Oracle APEX'   -> 24.2.14  VALID
# ORDS installed_version       -> 26.1.0.r0791128
# v$version                    -> Oracle AI Database 26ai EE 23.26.2.1.0
# APEX schema                  -> APEX_240200
# sqlplus / as sysdba          -> ORA-01017 (denied, both default and -u oracle)
# adb-cli commands             -> add-database, change-expired-password, change-password,
#                                 cleanup-container-data-dir, export, import, set-http-proxy
# image tag latest-26ai        -> 26.2.4.2-26ai  (ADBS build #, NOT the APEX version)
# APEX 26.1 zip (OTN)          -> HTTP 200, 325,993,509 bytes (apex_26.1.zip)
```

---

## Codebase Analysis

### Key locations

| File | Lines | Purpose |
|---|---|---|
| `tools/oracle/database.py` | 67 | Image pinned to `adb-free:latest-26ai` |
| `tools/oracle/database.py` | 467–476 | `_exec_sysdba_sql()` runs `sqlplus -S / as sysdba` — **assumes SYS works (it does not)** |
| `tools/oracle/database.py` | 454–465 | `configure_vector_memory()` depends on that SYSDBA path |
| `tools/oracle/database.py` | 478–554 | `initialize_db_users()` — connects as **ADMIN** via wallet, creates `app`, enables ORDS REST |
| `tools/oracle/database.py` | 232–234 | Prints APEX/Database Actions URLs (`/ords/apex`, `/ords/sql-developer`) |
| `tools/oracle/cli/database.py` | 42–176 | `infra`-group container lifecycle commands (start/stop/restart/remove/logs/status) |
| `tools/oracle/cli/sqlcl.py` | 21–114 | **SQLcl already integrated** (install/verify/uninstall) — host for `apex export/import` |
| `tools/oracle/sqlcl_installer.py` | — | SQLcl installer used by the above |
| `src/app/cli/commands.py` | 159–171 | `coffee upgrade` = migrations + fixtures (packaged install) |
| `manage.py` | 74–90 | `manage.py infra` group (wraps `tools/oracle/cli/database.py`) |
| `manage.py` | 98–109 | `manage.py database` group (wallet, connect) |
| `tools/oracle/on_init/02_create_apex_workspace.sh` | **deleted** | Old APEX `COFFEE` workspace provisioner (gvenzl hook era) |

### Current container/APEX provisioning walkthrough

1. `make start-infra` → `manage.py infra start --recreate` → `OracleDatabase.start()` (`database.py:153`).
2. `_build_run_command()` (`database.py:716`) runs `adb-free:latest-26ai` with TLS/mTLS/HTTPS/Mongo ports,
   `SYS_ADMIN`+`/dev/fuse`, and bind-mounts `.envs/tns` so the wallet is written to the host.
3. After healthy: `configure_vector_memory()` (SYSDBA exec), `_patch_host_sqlnet_ora()`,
   `initialize_db_users()` (ADMIN-via-wallet creates `app`, grants, `ORDS.ENABLE_SCHEMA`).
4. APEX/ORDS/Database Actions are served by the image's bundled stack at `https://localhost:8443/ords/*`.
   **The bundled APEX is 24.2.14** — nothing in the codebase installs or upgrades APEX.

### Constraints discovered

- The branch deliberately adopted `adb-free` for ADB parity (wallet/mTLS at `database.py:777`,
  Database Actions/Mongo, `ORDS.ENABLE_SCHEMA` at `:541–549`, OEE workspace). Reverting to a
  SYS-capable base reclaims APEX control but **discards these** — a real architectural reversal of the
  just-closed `oracle-apex-integration` flow.
- **No SYS access** means *any* APEX lifecycle action requiring SYSDBA (install/upgrade/patch) is
  impossible inside `adb-free`. ADMIN is the ceiling, and ADMIN cannot run `apexins.sql`.
- Free-tier SGA is capped (~2G); unrelated but bounds what the container can host.

### Corroborating note for the vector-memory path (cross-team, not actioned here)

`_exec_sysdba_sql()` (`database.py:467`) is built on `sqlplus / as sysdba`, which this research found
returns **ORA-01017** in the live container. That is the exact open question
`research_adb_hooks_ux_lab` flagged ("does `sqlplus / as sysdba` actually work inside adb-free?"). The
empirical answer is **no**. Whoever owns the vector-memory hardening should re-verify whether
`configure_vector_memory()` is silently failing or whether a different auth path is in effect. Flagged
here only because it shares the root cause (ADB SYS lockdown); no change made under this research.

---

## External Documentation (validated)

### Oracle APEX 26.1 / APEXlang
- **APEX 26.1** — GA 2026-05-14. Headline: **APEXlang**, CSP compliance (drops `unsafe-inline`/
  `unsafe-hashes`), AI Interactive Reports, AI Agents, Data Reporter.
- **APEXlang** — open, declarative, human-readable application spec. Export from App Builder or author
  directly; native support in **Oracle SQL Developer for VS Code** and **SQLcl**. `.apx` files are the
  source-of-truth in git: reviewable, diffable, mergeable, validatable.
- **Export structure** (`apex export -applicationid <id> -exptype apexlang`):
  `application.apx`, `pages/` (e.g. `p00001-dashboard.apx`), `shared-components/`,
  `supporting-objects/`, `deployments/` (incl. `default.json`), `.apex/apexlang.json`.
- **Prereq:** APEX **26.1 on both source and target** for validate/import. Single-page APEXlang import
  is not supported in this release (full-app only).

### ADB Free container upgrade reality
- Image tags: `latest-26ai` / `26.2.4.2-26ai`, `latest`/`26.2.4.2` (19c), and the deprecated
  `25.9.3.2-23ai`. The `26.2.4.2` is the **ADBS build number**, independent of the bundled APEX version.
- Oracle docs (Free Container): *"There is no automatic patching or maintenance windows for the Free
  Container Image. The repository provides the latest version… Check the repository to find newer
  versions."* Supported upgrade = **new image + DataPump migrate** (`adb-cli export`/`import`).
- Oracle hints images "often have an additional important-feature tag" — so a 26.1-bearing 26ai image
  **may** appear, but there is no commitment or date.
- Cloud ADB only: APEX upgrades are self-service via **APEX Administration Services** (apply now / defer
  up to 90 days). Patch-set bundles auto-apply; major releases reach a region 2–5 weeks after GA. None
  of this machinery exists in the free container.

### Manual APEX upgrade mechanics (relevant only to a SYS-capable base)
- As SYS to the PDB: `@apexins.sql SYSAUX SYSAUX TEMP /i/`, then `@apex_rest_config.sql`, then
  `@apxchpwd.sql`; ORDS serves images from `/i/`. Can take many minutes (object recompile).
- **APEX zip is a public no-login download** — `https://download.oracle.com/otn_software/apex/apex_26.1.zip`
  (verified HTTP 200, ~326 MB) — so a fully automated download+install command is feasible.

---

## Options

### Path A — Image-refresh upgrade command (keep `adb-free`, preserve ADB parity)
Add `manage.py infra upgrade`: `adb-cli export` the app schema → `docker pull` newer `adb-free` tag →
recreate container → `adb-cli import` → re-run `initialize_db_users()` / migrations / fixtures.

- **Pros:** keeps wallet/mTLS, Database Actions, Mongo, OEE; mirrors Oracle's *only* supported upgrade
  story; low architectural change; the command is reusable for every future image bump.
- **Cons:** **does not deliver APEX 26.1 today** (latest `26ai` image = 24.2.14). 26.1 depends entirely
  on Oracle shipping a 26.1-bearing image — **uncontrollable timing**, unsafe to bet a KScope date on.
  APEXlang/`src/apex/` stays blocked until then. DataPump migrate adds operational risk to demo data.

### Path B — SYS-capable base + manual APEX 26.1 (guarantee 26.1 now) — *recommended for the KScope goal*
Switch the dev DB image to `container-registry.oracle.com/database/free` (26ai) + ORDS sidecar
(`container-registry.oracle.com/database/ords`). Add `manage.py infra apex-upgrade --to 26.1`:
download the public zip → `apexins.sql` (as SYS) → `apex_rest_config.sql` → `apxchpwd.sql` → point ORDS
`/i/` at the new images.

- **Pros:** **guarantees APEX 26.1 today**; full version control independent of Oracle's cadence; the
  upgrade command is itself an on-point demo for an APEX-focused conference; unblocks APEXlang/`src/apex/`.
- **Cons:** **reverses the `oracle-apex-integration` migration** — loses ADB parity (no wallet/mTLS, no
  Database Actions, no Mongo API, no OEE workspace); reintroduces an ORDS sidecar to orchestrate;
  touches `settings.py`/`utils.py`/wallet flow that were just aligned to ADB.

### Path C — Parallel APEX-authoring container (lowest blast radius, two stacks)
Keep `adb-free` as the runtime demo DB; stand up a *separate* DB Free 26ai + APEX 26.1 + ORDS purely
for **authoring** the APEXlang app. Export `.apx` to `src/apex/`. The committed `.apx` is the artifact
shown at KScope.

- **Pros:** no change to the validated runtime stack; guarantees 26.1 for authoring; cleanly isolates
  the conference deliverable.
- **Cons:** two DB stacks to run/maintain; the demo's live DB still can't *run* a 26.1 app; conceptually
  muddy ("which database is the demo?"). Cuts against the project's simplicity mandate.

---

## Recommended Approach

For an **APEX-focused conference with a fixed date**, the binding requirement is *guaranteed APEX 26.1*
(APEXlang cannot run on 24.2). Oracle's image cadence cannot be relied on for that date, so:

1. **Decide the base-image fork explicitly (PRD decision).** Recommend **Path B** if the demo must
   *run* a 26.1 APEX app live at KScope; choose **Path C** if you only need the APEXlang `src/apex/`
   artifact and want zero risk to the validated `adb-free` runtime.
2. **Quick win first (do this regardless):** check the registry now for a 26.1-bearing `26ai`/feature
   tag — `docker pull` it and re-query `apex_release`. If one already exists, **Path A becomes trivial
   and dominates** (keeps ADB parity, delivers 26.1). Today's `latest-26ai` does not, but this is a
   5-minute recurring check worth scheduling against the KScope date.
3. **Build the management command in the right home.** Container/APEX lifecycle is a *maintainer/dev*
   concern → it belongs under **`manage.py infra`** (next to `start/stop/restart`), **not** on `coffee`
   (which is the packaged end-user installer). Reuse the existing SQLcl integration
   (`tools/oracle/cli/sqlcl.py`) for the APEX/APEXlang verbs.
4. **Define `src/apex/` now** (path-independent): one folder per app alias, e.g.
   `src/apex/cymbal_coffee/{application.apx, pages/, shared-components/, supporting-objects/,
   deployments/, .apex/}`. Add `manage.py infra apex-export` / `apex-import` wrapping
   `sqlcl … apex export -applicationid <id> -exptype apexlang -dir src/apex/<alias>`.
5. **Correct the record.** Mark `research_apex_integration`'s "APEX 26.1 pre-installed" / "SSO wall" /
   "sysdba works" claims as superseded by this validated research to prevent the bad assumption from
   propagating into the new PRD.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Bet on Oracle shipping a 26.1 `adb-free` image before KScope; it doesn't | High | High | Don't gate the conference on it; choose Path B/C for a guaranteed 26.1; keep Path A as the long-term parity story |
| Path B reversal destabilizes the just-validated ADB stack (settings/wallet/tests) | Medium | High | Branch-isolate; keep `adb-free` flow intact behind config; port `initialize_db_users` ADMIN logic to a SYS/PDB_DBA equivalent; full `make test` gate |
| Manual `apexins.sql` upgrade is long/fragile; ORDS `/i/` image mismatch | Medium | Medium | Pin exact ORDS↔APEX versions; script idempotently; verify `apex_release` + a smoke app post-install |
| DataPump migrate (Path A) loses/corrupts demo data across image bump | Medium | Medium | Re-derive demo data from committed fixtures (`coffee upgrade`) instead of trusting DataPump round-trip |
| `src/apex/` app drifts from the DB it was exported from (26.1-only import) | Medium | Low/Med | CI check: export must be 26.1; treat `.apx` as source-of-truth, re-import on setup |
| Vector-memory SYSDBA path silently broken on `adb-free` (cross-team) | Medium | High | Hand the ORA-01017 finding to the vector-memory owner; out of scope here |

**Rollback / checkpoints:** Path A is reversible (re-pull prior tag, re-import). Path B/C must live on a
dedicated branch with the `adb-free` config preserved so a single revert restores the validated runtime.
`src/apex/` additions are pure additions (no runtime coupling) and safe to land independently.

---

## Open Questions (for the PRD)

1. **Must the demo *run* a live APEX 26.1 app at KScope, or is the committed `src/apex/` APEXlang
   artifact sufficient?** This single answer selects Path B (run-live) vs Path C (artifact-only).
2. If Path B: is losing ADB parity (wallet/mTLS, Database Actions, Mongo API, OEE) acceptable for the
   demo, or is parity a hard requirement that forces Path A + waiting on Oracle?
3. Has Oracle published *any* `26ai`/feature-tagged `adb-free` image carrying APEX 26.1 yet? (Pull-and-
   check; flips the recommendation to Path A if yes.)
4. Which APEX app(s) become the Cymbal Coffee APEXlang deliverable, and what is the canonical app
   alias/ID for the `src/apex/<alias>/` layout?
5. Command surface: one `manage.py infra apex` subgroup (`upgrade`, `export`, `import`, `version`) vs.
   individual commands?

## Research Outputs

**This research informs:**
- PRD: `.agents/specs/{prd_id}/prd.md` (when created)
- Flow: `.agents/specs/{flow_id}/` (when created)
- Supersedes the inaccurate version/SSO/sysdba claims in
  `.agents/research/research_apex_integration/research.md`.

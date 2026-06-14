# Master PRD: ADB-Free Runtime Hardening, Oracle Linux/Podman Lab, and UI Quality

*PRD ID: `adb-podman-lab-hardening`*
*Beads Epic: `oracledb-vertexai-9p5`*
*Created: 2026-06-14*
*Status: Planning — Chapter 1 ready for `/flow:implement`*
*Research: `.agents/research/research_adb_hooks_ux_lab/research.md`*
*Builds on: completed PRD `oracle-apex-integration` (gvenzl → adb-free migration)*

---

## North Star

The Cymbal Coffee demo bootstraps reliably on **podman + Oracle Linux** with a correct, self-healing vector-memory startup path; the workshop lab is rewritten as a **single canonical Oracle Linux 9 + rootless podman track** with every accuracy defect fixed; and the chat/explore UI is accessible and correct.

---

## Background & Problem

The `oracle-apex-integration` PRD migrated the local DB from `gvenzl/oracle-free` to the official `container-registry.oracle.com/database/adb-free:latest-26ai`. That migration silently changed the container's hook contract:

- `gvenzl/oracle-free` natively runs mounted scripts from `/container-entrypoint-initdb.d` (once) and `/container-entrypoint-startdb.d` (every start) as SYSDBA. The old `tools/oracle/on_init/` + `on_startup/` directories depended on this.
- The official `adb-free` image has **no such mechanism** (confirmed against the `oracle/adb-free` README and Oracle docs). Those mounts would be silently ignored, so the branch correctly deleted them and moved vector-memory configuration to a post-start `exec … sqlplus -S / as sysdba` call (`tools/oracle/database.py:454-476`).

What remained imperfect:

1. **The every-start safety net was lost.** The deleted `on_startup/00_verify_vector_memory.sql` re-verified the vector pool on every DB start. The new path only checks during the CLI `start()` — and `database.py:192-201` early-returns past `configure_vector_memory()` when restarting an existing stopped container (masked today only because `make start-infra` passes `--recreate`).
2. **Silent-failure surface.** If `/ as sysdba` OS-auth or the bounce ever fails on `adb-free`, the pool stays 0 and the only symptom is a downstream `ORA-51962` during migration.
3. **The lab targets the wrong platform.** `tools/scripts/lab.md` provisions an Ubuntu 22.04 VM and installs docker, but the project's audience is Oracle users (Oracle Linux + podman), and the repo tooling already auto-detects podman and uses `:z` SELinux relabels.
4. **The lab has factual defects** (non-existent Valkey container, wrong data counts, a German paragraph, fragile whole-file drop-ins, lossy BigQuery example).
5. **UI defects** (telemetry popover stays `aria-hidden` while open; undefined SQL CSS classes; mobile grid overflow; `aria-live` streaming spam; dead code).

---

## Reviewed Sources

- `tools/oracle/database.py` — `DatabaseConfig` (image `:67`), `start()` early-return gap (`:192-201`), `configure_vector_memory()` (`:454-465`), `_exec_sysdba_sql()` (`:467-476`), `_build_run_command()` flags incl. `:z`, `SYS_ADMIN`, `/dev/fuse`, `--health-cmd` (`:742-799`).
- `tools/oracle/container.py` — `detect_runtime()` prefers docker, falls back to podman (`:45-73`).
- `tools/oracle/configure_vector_memory.sql` — standalone non-Free 4G helper.
- `Makefile:332-334` — `start-infra` → `manage.py infra start --recreate`.
- `tools/scripts/lab.md` — docker/Ubuntu workshop with verified factual defects.
- `src/resources/{main.js,styles.css}`, `templates/pages/{chat,explore}.html.j2`, `partials/_metrics_badges.html.j2` — UI findings.
- `.agents/research/research_adb_hooks_ux_lab/research.md` — full analysis + sources.

---

## Product Decisions

1. **Keep the post-start SYSDBA exec model; don't reintroduce hook dirs.** It's the only native path on `adb-free`. Make it self-healing (every-start verification) and loud (raise if the pool stays 0).
2. **Keep the in-session bounce.** `ALTER SYSTEM … SCOPE=SPFILE` + `SHUTDOWN IMMEDIATE/STARTUP` is user-endorsed and works; mitigate the "Oracle documents container-restart only" risk with a reproducible smoke test rather than a rewrite.
3. **Single canonical lab on Oracle Linux 9 + rootless podman.** Drop the Ubuntu/docker track entirely. Use `oracle-linux-cloud` GCE images (no license fee), `dnf` instead of `apt`, podman instead of docker, and remove Debian-only steps (`needrestart`, `usermod -aG docker`).
4. **Fix all verified lab inaccuracies** and convert fragile whole-file drop-ins to targeted snippets.
5. **UI: High + Med + verified cleanup**, honoring the repo's no-dead-code mandate (remove the dead non-stream path only after confirming it's unused).

---

## Global Constraints

- No backwards-compat shims; delete superseded code/docs outright (per project conventions).
- Floor-only dependency pins; no ceilings.
- `make lint` and `make test` are the aggregate gates before any chapter is "done."
- Oracle uses `:name` binds and `VECTOR(3072, FLOAT32)`; HNSW INMEMORY needs non-zero `vector_memory_size`.
- Coordinate privacy / no-key Maps URL behavior must be preserved by any UI change.
- Embedding model is `gemini-embedding-2-preview` / 3072 dims everywhere (resolve the naming drift in docs).

---

## Roadmap (Chapters)

| # | Chapter | Beads | Depends on | Summary |
|---|---------|-------|------------|---------|
| 1 | ADB-Free vector-memory startup hardening + podman/OL runtime validation | `9p5.1` | — | Self-healing every-start vector-memory check, fail-loud, podman/OL validation, SYSDBA bounce smoke test, doc alignment. **Foundation the lab depends on.** |
| 2 | Lab overhaul — Oracle Linux + podman + accuracy fixes | `9p5.2` | Ch1 | Rewrite `lab.md` for OL9 + rootless podman; fix Valkey/count/model/German/drop-in/BigQuery defects; fix README counts. |
| 3 | UI UX/correctness fixes (High + Med + verified cleanup) | `9p5.3` | — | a11y popover, SQL CSS, mobile grid, aria-live streaming; remove verified dead code + duplicate presets. |

Sequencing: **Ch1 → Ch2 → Ch3.** Ch2 is Beads-blocked by Ch1 (the lab must document a runtime validated on podman/OL). Ch3 is independent and can proceed in parallel but is sequenced last per scope decision.

---

## Success Metrics

- `make start-infra` succeeds end-to-end under rootless podman on Oracle Linux 9 (SELinux enforcing), and `coffee upgrade` builds HNSW indexes without `ORA-51962`.
- Restarting a stopped container (no `--recreate`) re-verifies and, if needed, re-applies the vector pool.
- A fresh workshop attendee following the rewritten `lab.md` on an OL9 VM reaches a working `/explore` page with no docker/apt/Valkey steps and no factual mismatches.
- UI: telemetry popover is screen-reader accessible when open; SQL bind rows render styled; no horizontal overflow on a 375px viewport; `make lint`/`make test` green.

---

## Out of Scope

- Switching the bounce to a container restart (revisit only if the Ch1 smoke test shows supervisor races).
- Moving demo data off `/dev/shm` tmpfs (documented as a known reboot caveat; auto-healed by the every-start check).
- New features in the BigQuery/Maps challenges beyond correctness fixes to the existing examples.
- The separate `oracledb-vertexai-inv` inventory epic.

---

## Next Step

Chapter 1 is planned and implementation-ready (`spec.md` at `.agents/specs/adb-vector-memory-hardening/spec.md`, tasks `9p5.1.1`–`9p5.1.5`). Run **`/flow:implement`** to begin.

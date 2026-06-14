# Flow: adb-vector-memory-hardening

*Chapter 1 of PRD `adb-podman-lab-hardening` (Beads epic `oracledb-vertexai-9p5.1`)*
*Research: `.agents/research/research_adb_hooks_ux_lab/research.md`*

## Specification

Make Oracle 26ai vector-memory configuration **self-healing on every container start** and **fail loudly** when it cannot be applied, and **validate the SYSDBA bounce path under rootless podman on Oracle Linux 9**. This restores the every-start safety net that was lost when the project moved from `gvenzl/oracle-free` (which ran `/container-entrypoint-startdb.d` hooks) to the official `adb-free` image (which has no such hooks). The in-session `ALTER SYSTEM … SCOPE=SPFILE` + `SHUTDOWN/STARTUP` bounce is intentionally retained.

### Requirements

- `OracleDatabase.start()` runs the idempotent `V$SGAINFO` vector-memory check on **every** path — new container, `--recreate`, and plain restart of an existing stopped container — not only the fresh-create path.
- `configure_vector_memory()` re-reads `V$SGAINFO` after configuring; if the pool is still 0, it raises `ContainerStartError` naming a blocked `/ as sysdba` or failed bounce as the likely cause (no silent fall-through to a later `ORA-51962`).
- The container lifecycle works under **rootless and rootful podman on Oracle Linux 9 with SELinux enforcing**: `:z` volume relabels, `--cap-add SYS_ADMIN`, `--device /dev/fuse`, `--shm-size`, `--restart`, `--health-cmd`, and health-status inspection all behave correctly; `detect_runtime()` selects podman when docker is absent.
- A reproducible smoke test proves `/ as sysdba` OS-auth + the SPFILE bounce yields a non-zero `Vector Memory` pool on `adb-free:latest-26ai`; the result is recorded in `learnings.md`.
- Docs (`oracle-vector-search.md`, `migrations/README.md`) state the adb-free hook reality, the every-start verification behavior, and a consistent embedding model name.

### Code Analysis Summary

- `tools/oracle/database.py:192-201` — existing-stopped-container branch calls `runtime.run_command(["start", …])` then `return`s, skipping `configure_vector_memory()`, `_patch_host_sqlnet_ora()`, and `initialize_db_users()`. This is the gap.
- `tools/oracle/database.py:218-223` — happy path order: `wait_for_healthy` → `configure_vector_memory()` → patch wallet → init users.
- `tools/oracle/database.py:454-465` — `configure_vector_memory()`: idempotent `V$SGAINFO` check, configure, re-wait healthy. No post-config re-verification.
- `tools/oracle/database.py:467-476` — `_exec_sysdba_sql()`: `exec <container> bash -lc "sqlplus -S / as sysdba <<SQL …"`.
- `tools/oracle/database.py:742-799` — run flags (already podman-friendly: `:z`, `SYS_ADMIN`, `/dev/fuse`).
- `tools/oracle/container.py:45-73` — runtime detection prefers docker, falls back to podman; `:408-414` reads `{{.State.Health.Status}}`.
- `Makefile:332-334` — `start-infra` passes `--recreate` (masks the gap today).
- Tests: `src/tests/unit/tools/oracle/test_database.py` exists and is already modified on this branch — extend it.

## Implementation Plan

### Phase 1: Every-start verification (`9p5.1.1`)
- [ ] 1.1 Restructure `start()` so the existing-stopped-container branch (`database.py:192-201`) starts the container, waits for health, then runs `configure_vector_memory()` (and, as appropriate, the wallet patch) instead of returning early.
- [ ] 1.2 Ensure the check stays idempotent (no double bounce when the pool is already non-zero) and does not re-run destructive user-init when not needed.
- [ ] 1.3 Unit test: restarting a stopped, already-initialized container triggers the `V$SGAINFO` check (mock `_exec_sysdba_sql`).

### Phase 2: Fail-loud configuration (`9p5.1.2`)
- [ ] 2.1 In `configure_vector_memory()`, after the bounce + `wait_for_healthy`, re-read `V$SGAINFO`; if still 0, raise `ContainerStartError` with a diagnostic message (sysdba/bounce likely cause).
- [ ] 2.2 Unit test: a stubbed `_exec_sysdba_sql` returning 0 bytes post-config raises `ContainerStartError`.

### Phase 3: Podman + Oracle Linux validation (`9p5.1.3`)
- [ ] 3.1 Run `make start-infra` under podman on an OL9 host (SELinux enforcing); confirm `:z` relabels, `SYS_ADMIN`/`/dev/fuse`, and health polling work; capture any flag deltas.
- [ ] 3.2 Confirm `detect_runtime()` returns PODMAN when docker is absent; confirm `inspect --format {{.State.Health.Status}}` parity on podman 4+.
- [ ] 3.3 Record any podman/OL-specific adjustments (e.g., rootless device passthrough) in `learnings.md`; apply minimal code changes only if a flag is incompatible.

### Phase 4: SYSDBA bounce smoke test (`9p5.1.4`)
- [ ] 4.1 Add a documented, reproducible smoke test (script or doc steps) for `sqlplus -S / as sysdba` + `ALTER SYSTEM SET vector_memory_size=512M SCOPE=SPFILE` + `SHUTDOWN/STARTUP` → non-zero `Vector Memory` in `V$SGAINFO` on `adb-free:latest-26ai`.
- [ ] 4.2 Record the result (and confirmation the in-session bounce is safe vs the container supervisor) in `learnings.md`.

### Phase 5: Doc alignment (`9p5.1.5`)
- [ ] 5.1 Update `.agents/knowledge/guides/oracle-vector-search.md` (embedding model name at line 9 → match `settings.py:349`) and add the "adb-free has no entrypoint hook dirs" rationale + every-start verification note.
- [ ] 5.2 Update `src/app/db/migrations/README.md` to remove any implication that `on_init`/`on_startup` hook dirs apply to adb-free.

### Verification Gate
- [ ] `make lint` and `make test` green.
- [ ] `make start-infra` → `coffee upgrade` builds HNSW indexes with no `ORA-51962`, under podman on OL9.
- [ ] Update Beads task states and run `/flow:sync`.

## Notes / Decisions
- Keep the in-session bounce (do not switch to container restart) — revisit only if Phase 4 shows supervisor races.
- `/dev/shm` tmpfs means the SPFILE pool is lost on host reboot; Phase 1's every-start check auto-heals this. Documented as a known caveat, not fixed here.
- Pool stays at 512M (Free SGA cap); the 4G `tools/oracle/configure_vector_memory.sql` is non-Free only.

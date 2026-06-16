# Research: ADB-Free Startup Hooks, UI Quality, and lab.md Accuracy

**Workspace**: `.agents/research/research_adb_hooks_ux_lab/`
**Status**: Complete
**Type**: Integration / Refactoring (container lifecycle) + Quality review (UI, docs)
**Date**: 2026-06-14
**Branch**: `feat/inv`

## Executive Summary

- **The startup-hook regression is a direct consequence of switching container images.** `main` ran `gvenzl/oracle-free:latest`, which natively executes mounted scripts in `/container-entrypoint-initdb.d` (once) and `/container-entrypoint-startdb.d` (every start). This branch switched to the **official** `container-registry.oracle.com/database/adb-free:latest-26ai`, which has **no such hook mechanism** (confirmed against the `oracle/adb-free` README and Oracle docs). The old `on_init/` + `on_startup/` mounts would have been silently ignored on the new image — so deleting them and moving vector-memory config to a post-start `sqlplus / as sysdba` exec was the correct direction.
- **What was lost is the "every-start" safety net.** The deleted `on_startup/00_verify_vector_memory.sql` re-verified the vector pool on *every* DB start. The new design only configures/verifies during the CLI `start()` path, and even then **skips it when restarting an existing stopped container** (`tools/oracle/database.py:199` early-returns before `configure_vector_memory()`). `make start-infra` masks this because it passes `--recreate`.
- **Two load-bearing assumptions in the new path need empirical validation**: (a) that `sqlplus / as sysdba` OS-auth works inside `adb-free` (ADB normally hides SYS), and (b) that in-session `SHUTDOWN IMMEDIATE; STARTUP` is safe inside the container vs. racing the container supervisor. Oracle's own guidance is to **restart the container** to bounce the instance.
- **UI review surfaced 2 High issues** (telemetry popover stays `aria-hidden` while open; undefined `help-tooltip-metric*` CSS classes leave SQL bind rows unstyled) plus a mobile grid-overflow bug and several dead-code/dup-preset cleanups.
- **lab.md has 3 factual errors that will mislead attendees**: the "Valkey caching instance" doesn't exist (single Oracle container, Oracle-backed cache), the "122 coffee items / 16 stores" counts are wrong (130 products / 17 stores), and a paragraph in Challenge 2 is in German. The BigQuery drop-in also silently loses failed writes.

## Research Tasks Summary

| Task | Status | Key Findings |
|------|--------|--------------|
| Oracle container hook mechanism (main vs branch) | Complete | gvenzl hooks ≠ adb-free; new post-start exec is correct direction but lost every-start verification |
| Official adb-free hook capability (web) | Complete | No init/startup hook dirs in official image; post-startup SQL is the documented path |
| UI components quality (subagent) | Complete | 2 High (a11y popover, undefined CSS), 1 Med grid overflow, dead code/dup presets |
| lab.md accuracy/simplicity (subagent) | Complete | Valkey claim false, data counts wrong, German text, fire-and-forget BQ logging |

---

## Part 1 — Oracle ADB-Free Container & SYSDBA Startup Hooks

### Codebase Analysis

| File | Lines | Purpose |
|------|-------|---------|
| `tools/oracle/database.py` | 67 | Image = `container-registry.oracle.com/database/adb-free:latest-26ai` |
| `tools/oracle/database.py` | 40–46 | `VECTOR_MEMORY_CONFIG_SQL`: `ALTER SYSTEM SET vector_memory_size=512M SCOPE=SPFILE; SHUTDOWN IMMEDIATE; STARTUP` |
| `tools/oracle/database.py` | 454–465 | `configure_vector_memory()` — idempotent check via `V$SGAINFO`, then configure + re-wait healthy |
| `tools/oracle/database.py` | 467–476 | `_exec_sysdba_sql()` — `docker exec … sqlplus -S / as sysdba <<SQL` |
| `tools/oracle/database.py` | 192–201 | **Gap:** existing stopped container path `return`s before `configure_vector_memory()` |
| `tools/oracle/database.py` | 219–223 | Happy path: `wait_for_healthy` → `configure_vector_memory()` → `_patch_host_sqlnet_ora()` → `initialize_db_users()` |
| `tools/oracle/configure_vector_memory.sql` | 24–31 | Standalone DBA helper: 6G SGA + 4G pool (non-Free only), SHUTDOWN/STARTUP |
| `Makefile` | 332–334 | `start-infra` → `manage.py infra start --recreate` (so vector memory IS configured in the default flow) |

**Historical approach (`main`, via `git show main:tools/oracle/database.py`):**
- Image: `gvenzl/oracle-free:latest` (`:28`).
- `_build_run_command` mounted `tools/oracle/on_init/*.{sql,sh}` → `/container-entrypoint-initdb.d/` (`:498–509`) and `tools/oracle/on_startup/*.{sql,sh}` → `/container-entrypoint-startdb.d/` (`:511–520`).
- Deleted `on_init/00_configure_vector_memory.sql` set `vector_memory_size=512M SCOPE=SPFILE` + `SHUTDOWN/STARTUP` as the first init step; its own header comment documents that **"gvenzl/oracle-free executes /container-entrypoint-initdb.d/*.sql in alphabetical order as SYSDBA on the CDB."**
- Deleted `on_startup/00_verify_vector_memory.sql` re-checked `V$SGAINFO` on every start and warned if zero (the lost safety net).
- Deleted `on_init/db_init.sql` granted app privileges; `on_init/02_create_apex_workspace.sh` provisioned the APEX `COFFEE` workspace. On the branch these moved into `initialize_db_users()` (`:478–554`) and (per commit `26867ad`) APEX provisioning.

### Library / Platform Documentation

**gvenzl/oracle-free** ([container-entrypoint.sh](https://github.com/gvenzl/oci-oracle-free/blob/main/container-entrypoint.sh)): supports `/container-entrypoint-initdb.d` (run once, after DB creation) and `/container-entrypoint-startdb.d` (run on every start; also legacy `/docker-entrypoint-startdb.d`). Files run in alphabetical order as SYSDBA. **This is what `main` relied on.**

**Official `oracle/adb-free`** ([README](https://github.com/oracle/adb-free), [Oracle docs](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/autonomous-database-container-free.html)): **No init/startup hook directories.** Documented surface is:
- First-start env vars only: `ADMIN_PASSWORD` (12–30 chars), `WALLET_PASSWORD` (≥8), `WORKLOAD_TYPE`, `DATABASE_NAME`, `ENABLE_ARCHIVE_LOG`.
- Post-startup admin via `adb-cli` (`add-database`, `change-password`) and ordinary SQL clients after the container is up.
- Instance Start/Stop/Restart are **not** exposed through ADB tooling; the documented way to bounce the instance is **"starting, stopping or restarting the container."**

**Vector pool sizing (26ai)** ([Size the Vector Pool](https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/size-vector-pool.html), [VECTOR_MEMORY_SIZE](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/VECTOR_MEMORY_SIZE.html)): `vector_memory_size` is static (`SCOPE=SPFILE`), requires a bounce, defaults to 0 (no pool). HNSW needs a non-zero pool or `ORA-51962`. PDB cap = 70% of PDB `sga_target`. Sizing ≈ `1.3 × rows × dims × element_size` — matches `oracle-vector-search.md:80–87`.

### Observations

- **Strength:** `configure_vector_memory()` is idempotent (`database.py:456–459`) — re-running `start --recreate` won't double-bounce a healthy pool.
- **Strength:** setting the param at CDB root via `/ as sysdba` with `SCOPE=SPFILE` is the right *location* for a static SGA parameter, and the code re-waits for health after the bounce (`:463`).
- **Concern (the regression):** there is no longer an every-start verification. The closest equivalent — the CLI `start()` path — `return`s early for an existing stopped container (`database.py:199`), so a plain restart never re-checks the pool. The deleted `on_startup` hook used to cover exactly this.
- **Concern (unverified SYSDBA):** real ADB hides SYS/SYSTEM and grants only `ADMIN`. Whether `sqlplus / as sysdba` OS-auth + `ALTER SYSTEM … SCOPE=SPFILE` actually succeeds inside `adb-free` is **not documented** and must be smoke-tested. If it is blocked, the entire post-start path fails silently for vector memory.
- **Concern (in-session bounce):** `SHUTDOWN IMMEDIATE; STARTUP` from inside the container fights the container's process supervisor + healthcheck (`--health-cmd` lsnrctl grep, `database.py:788–789`) and `--restart unless-stopped` (`:782–783`). Oracle's documented bounce is a **container restart**. The current code may work, but the safer, doc-aligned pattern is: set SPFILE param, then `docker restart`, then wait-for-healthy.
- **Concern (persistence):** data dirs default to `/dev/shm/*` tmpfs (`database.py:91–93`). The SPFILE survives a container restart but **not a host reboot / tmpfs wipe**; after a reboot the pool is gone and migrations/queries will hit `ORA-51962` unless `start()` re-applies it — which it currently won't on a non-`--recreate` restart.

### Constraints Discovered

- The branch deliberately adopted `adb-free` for 26ai + ADB capabilities (wallet/mTLS at `:777`, ORDS/APEX/Database Actions at `:232–234`, `ORDS.ENABLE_SCHEMA` at `:541–549`). Reverting to `gvenzl/oracle-free` to regain native hooks would lose those — not a real option.
- Free SGA is capped (~2G); pool stays at `512M` (`DEFAULT_VECTOR_MEMORY_SIZE`, `:27`). `sga_max_size`/`sga_target` overrides raise `ORA-56752` on Free — correctly avoided in the managed path and only used by the standalone non-Free `configure_vector_memory.sql`.

---

## Part 2 — UI Components (UX & Correctness)

Full audit covered `src/app/domain/web/templates/**` and `src/resources/{main.js,vector-calculator.js,styles.css}`, cross-checked against `_chat.py`, `_vector.py`, `_metrics.py`, and `adk.py`. SSE event names (`delta`/`final`/`error`), camelCase payloads, and `escapeHtml` usage all verified consistent — findings below are the real gaps.

### High

- **A11y — `pages/chat.html.j2:104`, `pages/explore.html.j2:243`:** telemetry popover root is hardcoded `aria-hidden="true"`; `showTelemetryPopover` (`main.js:264–306`) sets `root.hidden=false` and rewrites `className` but never removes `aria-hidden`. While open, the popover + its Close button + SQL/EXPLAIN content stay invisible to screen readers. Fix: `removeAttribute("aria-hidden")` on open, restore on close (or `role="dialog"` + focus mgmt).
- **Correctness — `main.js:155–156`:** `renderSqlPhase` emits `help-tooltip-metric` / `-label` / `-value` classes that exist in neither `styles.css` nor the built CSS nor Tailwind — SQL bind rows in the telemetry popover render unstyled (label/value collapse). Fix: use existing utilities (`flex justify-between text-xs`, `text-muted`, `font-mono text-strong`) or add the component classes.

### Medium

- **UX/Correctness — `styles.css:316–319`:** mobile `@media (max-width:47.999rem) .ui-panel{width:calc(100vw-2rem)}` forces a fixed viewport width on chat grid children (sidebar `<aside>` + thread `<div>`), fighting grid track sizing → horizontal overflow/misalignment on phones. Fix: scope to non-chat panels.
- **A11y/UX — `chat.html.j2:48` + `main.js:820–840`:** `#messages` is `aria-live="polite"` and deltas stream into `#pending-reply-text` inside it → erratic re-announcement token-by-token. Fix: announce only the finalized answer in a dedicated visually-hidden live region; mark the streaming node `aria-live="off"`.
- **A11y — `explore.html.j2:38–41`, `chat.html.j2:97`:** `required` on inputs submitted programmatically (`hx-trigger` / `fetch` + `preventDefault`) never fires native validation; chat has a JS empty-guard (`main.js:931`) but explore has none. Fix: rely on JS guard consistently + explore empty-state.

### Low (cleanup)

- **DeadCode — non-streaming chat path:** nothing wires `hx-post="/api/chat"`; `partials/_chat_response.html.j2` + `_metrics_badges.html.j2` (OOB, pill style) + `message.html.j2` metrics footer are dead vs the live `/api/chat/stream` + JS `renderMetrics` path (`main.js:89–112`). Confirm and remove.
- **DeadCode — unused `data-*` hooks** (`data-telemetry-chip-list`, `data-app-shell`, `data-app-header`, `data-ui-panel`, `data-metric-card`, `data-plan-row`, `data-plan-line`, `data-telemetry-chip`) never queried by JS.
- **Correctness — `explore.html.j2:121–144`:** "Gemini 3072" and "OpenAI 3072" presets are identical (both 3072/FLOAT32) — redundant. Differentiate by format or drop one.
- **UX — `explore.html.j2:69–70`:** trend label falls back to literal "up"/"down"/"neutral" for cards without `trend_value` (`_metrics.py:41–54`). Render trend only when present or map to a glyph.

**Top 5:** (1) popover `aria-hidden`, (2) undefined `help-tooltip-metric*` CSS, (3) scope mobile `.ui-panel` width, (4) stop streaming into `aria-live`, (5) delete dead non-stream path + dup preset.

---

## Part 3 — lab.md Accuracy, Correctness, Simplicity

Verified `tools/scripts/lab.md` against the repo. All CLI commands (`coffee upgrade/run/bulk-embed`, `make install/start-infra`, `manage.py init`, `manage.py assets build`), port `5006` (`-L8080:localhost:5006`), `SuperSecret1`/user `app` defaults, `VECTOR(3072,FLOAT32)`, HNSW INMEMORY, `gemini-2.5-flash-lite`, `/explore` existence, and both Challenge drop-ins' symbol references (`ChatMessage`, `CoffeeChatReply`, `ADKRunner`, `settings.maps.embed_enabled`, `settings.maps.EMBED_API_KEY`, `renderStoreCard` at `main.js:713`, `<body>` at `base.html.j2:19`) — **all PASS**.

### Accuracy issues (ordered)

1. **Valkey claim is false (Step 6.1–6.2).** Lab says `make start-infra` runs Oracle "alongside a Valkey caching instance" and to verify "both container systems." `start-infra` launches **one** Oracle container (`Makefile:332–334`, `database.py:64–87`); caching is Oracle-backed (`CacheService(OracleAsyncService)`, `system/services/services.py:131`) — zero `valkey`/`redis` references. Attendees will see one container via `docker ps` and think it failed. Fix: drop the Valkey sentence; "both container systems" → "the Oracle container."
2. **Data counts wrong (intro + Step 6.3).** "122 coffee items, 16 premium store locations" → actual `product.json.gz` = **130** products (108 `category=coffee`), `store.json.gz` = **17** stores. README repeats the stale numbers. Fix: "130 products … and 17 store locations."
3. **Embedding model drift (intro line 5).** Lab + guide say `gemini-embedding-2`; configured default is **`gemini-embedding-2-preview`** (`settings.py:349`; also `oracle-vector-search.md:9`). Fix: use `-preview` consistently or confirm the intended GA name.
4. **Challenge 1 BigQuery logging is silently lossy (lab.md:501–515).** `run_in_executor(None, log_to_bigquery)` discards the Future (exceptions never retrieved); `insert_rows_json` returns a per-row error list (doesn't raise) that's never inspected; only `except Exception: print(...)` — won't catch insert errors and uses `print` not the module `structlog` logger. Violates the project's no-silent-failure rule. Fix: inspect the returned errors list and log via `logger.aexception`/`awarning`.
5. **Distance-comparison overstated (Step 7.4).** `/explore` shows a single similarity-score % over a fixed `DISTANCE COSINE` index (`_vector.py:115–122`), not selectable Cosine/Euclidean side-by-side. The other three bullets (raw vector queries, latencies, EXPLAIN/DBMS_XPLAN/HNSW) are accurate. Fix: "cosine similarity scores."
6. **ADK "2.0" is beta** (`pyproject.toml` `google-adk>=2.0.0b1`) — minor overstatement; note only.

### Simplicity issues

1. **German paragraph in Challenge 2 Step A (lab.md:545–550)** — 5 lines + sub-steps in German in an English doc. Translate.
2. **Whole-file "drop-in replacements" will rot.** Challenge 1 (`_chat.py` ~230 lines) and Challenge 2 (`_pages.py`, 45-line `renderStoreCard`) say "select all, replace." They match today but silently diverge on any upstream change and they drop the real files' docstrings + `# docs:` markers. Prefer showing only the inserted block/diff.
3. **Redundant `assets build` (Step 7.2)** — `make install` already runs it (`Makefile:85`); only needed again after editing `main.js` in Challenge 2 Step E.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `sqlplus / as sysdba` blocked in adb-free → vector memory never configured | Medium | High | Smoke-test `docker exec <c> sqlplus -S / as sysdba` + `V$SGAINFO`; fail loudly in `configure_vector_memory()` if pool stays 0 after config |
| In-session `SHUTDOWN IMMEDIATE; STARTUP` races container supervisor/healthcheck | Medium | Medium | Switch bounce to SPFILE-set + `docker restart` + `wait_for_healthy` (matches Oracle's documented container-restart guidance) |
| Plain restart of existing container skips pool verification (`database.py:199`) | High (non-`--recreate` path) | Medium | Always run idempotent `configure_vector_memory()` check on every `start()` before returning |
| tmpfs (`/dev/shm`) wipe on host reboot drops SPFILE/pool | Medium | High | Document; the every-start check above auto-heals it, or move data off tmpfs |
| Popover `aria-hidden` while open | High | Medium (a11y) | Toggle `aria-hidden` with visibility |
| Lab Valkey/data-count errors mislead workshop attendees | High | Medium | Edit lab + README counts and the Valkey sentence |
| BigQuery drop-in loses failed writes silently | High (if used) | Low/Med | Inspect insert errors, log via structlog |

**Rollback / checkpoints:** All Part 1 changes are localized to `tools/oracle/database.py` (+ optional `oracle-vector-search.md`); revert with a single-file checkout. UI fixes are independent per-finding (template/JS/CSS) — land and verify one at a time. Lab edits are doc-only. No migrations or data changes implied; commit each part separately on `feat/inv`.

---

## Recommended Approach

**Part 1 (sysdba startup hooks) — recommended:** keep the post-start exec model (the only native path for `adb-free`) and harden it:
1. Run the **idempotent vector-memory check on every `start()`** (including the existing-stopped-container path at `database.py:192–201`) so it behaves like the lost `on_startup` verification and auto-heals after a tmpfs/host-reboot wipe.
2. **Bounce via container restart**, not in-session `SHUTDOWN/STARTUP`, to match Oracle's documented guidance and avoid supervisor races.
3. Make `configure_vector_memory()` **fail loudly** if `V$SGAINFO` is still 0 after configuring (catches a blocked `/ as sysdba`).
4. **Smoke-test** sysdba access + the bounce on `adb-free:latest-26ai` before relying on it; record the result in `learnings.md`.
5. Update `oracle-vector-search.md`/README so the model name and the "no hook dirs" rationale are consistent.

**Part 2 (UI):** ship the 2 High fixes + mobile grid scope first (a11y + correctness, user-visible), then the dead-code/dup-preset cleanup.

**Part 3 (lab):** apply the 3 factual fixes (Valkey, counts, German) + the model name; convert whole-file drop-ins to inserted snippets and fix the BigQuery logging example.

## Open Questions

- Does `sqlplus / as sysdba` (OS auth) actually work inside `adb-free:latest-26ai`, and does it permit `ALTER SYSTEM … SCOPE=SPFILE` + a bounce? (Requires live test — the single biggest unknown.)
- Is the non-streaming `/api/chat` HTML path still a supported client, or fully superseded by `/api/chat/stream`? (Determines whether to delete the dead partials.)
- Is `gemini-embedding-2` (GA) or `gemini-embedding-2-preview` the intended pinned model? (Docs/lab/settings disagree.)
- Should demo data persist across host reboots (move off `/dev/shm` tmpfs), or is re-bootstrap acceptable?

## Research Outputs

**This research informs:**
- PRD: `.agents/specs/{prd_id}/prd.md` (when created)
- Flow: `.agents/specs/{flow_id}/` (when created)

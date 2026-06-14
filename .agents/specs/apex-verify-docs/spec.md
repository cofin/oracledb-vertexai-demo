# Flow Spec: apex-verify-docs (Chapter 5)

*Beads: `oracledb-vertexai-apxg.5` (chapter epic)*
*Parent PRD: [../apex-gvenzl-install/prd.md](../apex-gvenzl-install/prd.md)*
*Depends on: Ch2 (install engine), Ch4 (APEXlang) — exercises the whole stack*
*Status: Implementation-ready*

---

## 1.0 Context

Final chapter: prove the full APEX lifecycle end-to-end, align the application's connection
settings/env to the reverted `gvenzl` base (service `FREEPDB1`, no wallet/mTLS), and document the new
workflow. The container-base revert is owned by a separate agent (task `oracledb-vertexai-2q0`); this
chapter owns the **app-side settings/env alignment** and the **docs**, and adds the integration smoke
gate. **`lab.md` is excluded** — it belongs to the concurrent `adb-podman-lab-hardening` effort.

---

## 2.0 Requirements

- App connects to gvenzl `FREEPDB1` over TCP (no wallet): `DatabaseSettings.SERVICE_NAME` default
  `FREEPDB1`, `is_autonomous` false by default; coordinate with the revert agent to avoid double-edits.
- `make`/CLI env scaffolding (`tools/lib/utils.py` managed mode) writes gvenzl defaults
  (`DATABASE_URL=oracle+oracledb://app:…@localhost:1521/FREEPDB1`, no `WALLET_*`).
- Deterministic unit tests for the Ch1–Ch4 modules are green (mocked exec/subprocess).
- An integration **smoke** path / make target: `install → workspace → ORDS → apex_release==26.1 →
  APEXlang export round-trip`.
- Docs updated: `quickstart`, `architecture`, `oracle-vector-search` (APEX/ORDS section), `CLAUDE.md`
  (commands + APEX notes). **No `lab.md` edits.**

---

## 3.0 Proposed Changes

### Component: app settings/env alignment (`src/app/lib/`, `tools/lib/`)
#### [MODIFY] `src/app/lib/settings.py`
- `DatabaseSettings.SERVICE_NAME` default → `FREEPDB1`; ensure `is_autonomous` is false without wallet;
  drop adb-free-only assumptions (no `myatp_*` default). Coordinate with the revert (may already land it).
#### [MODIFY] `tools/lib/utils.py`
- `create_env_interactive()` managed mode → gvenzl defaults (`FREEPDB1`, port 1521, no `WALLET_*`,
  no `TNS_ADMIN`). Remove ADB-only env keys.

### Component: tests (`src/tests/`)
#### [CREATE] `src/tests/integration/test_apex_lifecycle.py` (marked, opt-in)
- Real path against the running stack: assert `apex_release==26.1`, COFFEE workspace exists, `/ords/apex`
  reachable, and an export→import round-trip on a fixture app yields a stable diff.
#### [MODIFY] unit suites under `src/tests/unit/tools/oracle/`
- Ensure `test_apex_media`, `test_apex_install`, `test_apex_ords`, `test_apex_lang` all pass together.

### Component: build/docs
#### [MODIFY] `Makefile`
- Add `apex-smoke` target wrapping the integration smoke (guarded; not in default `make test`).
#### [MODIFY] docs
- `docs/reference/quickstart.md` — gvenzl + `infra apex install` + ORDS + APEXlang workflow.
- `.agents/knowledge/guides/architecture.md` — APEX/ORDS topology (sidecar, `/i/`, `FREEPDB1`).
- `.agents/knowledge/guides/oracle-vector-search.md` — note gvenzl base + SYSDBA availability.
- `CLAUDE.md` — `manage.py infra apex …` commands + "gvenzl base, APEX 26.1, ORDS sidecar" notes.

---

## 4.0 Implementation Plan (TDD)

- [ ] **Task 5.1** — Settings/env alignment for gvenzl (`SERVICE_NAME=FREEPDB1`, no wallet) +
  `utils.py` managed defaults; coordinate with revert. Unit tests: `is_autonomous` false, DSN shape.
- [ ] **Task 5.2** — Green the combined unit suites for Ch1–Ch4 modules (fix any cross-module drift).
- [ ] **Task 5.3** — Integration smoke test + `make apex-smoke` (install→workspace→ORDS→26.1→round-trip).
- [ ] **Task 5.4** — Docs: quickstart + architecture + oracle-vector-search + `CLAUDE.md` (exclude `lab.md`).
- [ ] **Task 5.5** — Final aggregate gate (`make lint` + `make test`) + record outcome in
  `.agents/specs/apex-gvenzl-install/learnings.md`.

---

## 5.0 Verification Plan

```bash
make lint
make test
make apex-smoke          # opt-in real lifecycle (needs running stack)
uv run python manage.py database connect test
```
- Confirms app connects to `FREEPDB1` (no wallet), APEX is 26.1, ORDS serves `/ords/apex`, APEXlang
  round-trips, and docs reflect the gvenzl + APEX 26.1 + ORDS workflow.

---

## 6.0 Definition of Done

- App boots/tests against gvenzl `FREEPDB1` with no wallet/mTLS; settings/env reflect the revert.
- All Ch1–Ch4 unit suites + the integration smoke pass; `make lint` + `make test` green.
- Docs updated (quickstart, architecture, oracle-vector-search, CLAUDE.md); `lab.md` untouched.
- `learnings.md` records the verified end-to-end outcome.

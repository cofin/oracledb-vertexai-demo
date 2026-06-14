# Flow Spec: apexlang-source (Chapter 4)

*Beads: `oracledb-vertexai-apxg.4` (chapter epic)*
*Parent PRD: [../apex-gvenzl-install/prd.md](../apex-gvenzl-install/prd.md)*
*Depends on: Ch2 (APEX 26.1 in `FREEPDB1`), Ch3 (running ORDS/APEX)*
*Status: Drafted — minor refresh before implementation (see contract update)*

---

> **⚠ Contract update (2026-06-14).** Largely intact (SQLcl-based), but align connection details to the
> landed gvenzl base when implementing: PDB/service `freepdb1` on `localhost:1521`, app/COFFEE schema with
> the gvenzl app-user credentials from `DatabaseConfig`. `apex_group` already exists from Ch2 in
> `tools/oracle/cli/apex.py` (export/import commands attach there). No `database.py` interaction.

## 1.0 Context

APEXlang (APEX 26.1) represents an application as a diffable tree of `.apx` files — the
source-of-truth for version control. SQLcl exports/imports it via
`apex export -applicationid <id> -exptype apexlang`. SQLcl is **already integrated**
(`tools/oracle/sqlcl_installer.py` installs the `sql` binary to `~/.local/bin/sql`;
`tools/oracle/cli/sqlcl.py` manages it). This chapter defines the `src/apex/<alias>/` layout and adds
`manage.py infra apex export | import` wrapping SQLcl, then proves a full-app round-trip. **Requires APEX
26.1 on both ends** (single-page APEXlang import is not supported in 26.1 — full-app only).

---

## 2.0 Requirements

- Establish `src/apex/<app_alias>/` as the committed APEXlang root with the standard structure:
  `application.apx`, `pages/`, `shared-components/`, `supporting-objects/`, `deployments/`, `.apex/`.
- `infra apex export --app-id <id> [--alias <name>]` → SQLcl `apex export … -exptype apexlang -dir
  src/apex/<alias>` against `FREEPDB1` as the app/COFFEE schema; deterministic, re-runnable (clean
  destination so diffs are stable).
- `infra apex import --alias <name>` → import the committed `.apx` tree back into the workspace.
- Locate `sql` via the existing `SQLclInstaller`; fail with install guidance if SQLcl is absent or not
  26.1-capable.
- A documented full-app round-trip: export → stable `git diff` → import succeeds.

---

## 3.0 Proposed Changes

### Component: APEXlang wrapper (`tools/oracle/`)

#### [CREATE] `tools/oracle/apex_lang.py`
- `@dataclass ApexLangConfig`: `src_root: Path = src/apex`, connection (FREEPDB1, app/COFFEE schema),
  `exptype = "apexlang"`.
- `class ApexLang(installer: SQLclInstaller, config)`:
  - `_sql_bin()` — resolve `sql` via `SQLclInstaller`; raise with install hint if missing.
  - `export(app_id: int, alias: str, *, clean=True) -> Path` — run
    `sql -S <conn>` piped `apex export -applicationid <id> -exptype apexlang -dir <src_root>/<alias>`;
    optionally clear the destination first for clean diffs; returns the export dir.
  - `import_app(alias: str) -> None` — import the committed tree (full-app) back into the workspace.
  - `validate(alias: str) -> bool` — optional APEXlang validation pass where supported.

### Component: source root + CLI

#### [CREATE] `src/apex/README.md` + `src/apex/.gitkeep`
- Document the `<alias>/` layout and that `.apx` is the source-of-truth (export to update, import to apply).

#### [MODIFY] `tools/oracle/cli/apex.py` (the `apex_group` from Ch2)
- Add `export` (`--app-id`, `--alias`) and `import` (`--alias`) commands building `ApexLang`.

---

## 4.0 Implementation Plan (TDD)

- [ ] **Task 4.1** — `src/apex/` root + `README.md` documenting the APEXlang layout; `.gitkeep`.
- [ ] **Task 4.2** — `ApexLang.export()` wrapping SQLcl `apex export -exptype apexlang -dir
  src/apex/<alias>` (+ clean-destination). Unit tests mock `sql` subprocess; assert argv + dir.
- [ ] **Task 4.3** — `ApexLang.import_app()` (+ optional `validate()`). Unit tests mock `sql`; assert
  full-app import argv and missing-SQLcl guidance.
- [ ] **Task 4.4** — `infra apex export|import` CLI wired into the `apex_group`. Unit tests via Click
  runner (mock `ApexLang`).
- [ ] **Task 4.5** — Documented full-app round-trip smoke (export → stable diff → import) in the spec's
  verification + `learnings.md`.

---

## 5.0 Verification Plan

### Automated
```bash
uv run pytest src/tests/unit/tools/oracle/test_apex_lang.py
make lint
```
- Deterministic: `sql` subprocess mocked; assert SQLcl argv and `src/apex/<alias>` target.

### Manual (real, after Ch2+Ch3 with a workspace app present)
```bash
uv run python manage.py infra apex export --app-id 100 --alias cymbal_coffee
git status src/apex/cymbal_coffee   # human-readable .apx tree
uv run python manage.py infra apex import --alias cymbal_coffee
# re-export -> git diff is empty/stable (round-trip)
```

---

## 6.0 Definition of Done

- `infra apex export` writes a diffable APEXlang tree under `src/apex/<alias>/`; `import` round-trips it
  on APEX 26.1.
- SQLcl is auto-located; absence yields clear install guidance.
- Re-export after import produces a stable diff; `make lint` and unit tests pass.

---

## Open Questions
- Canonical app alias/ID for `src/apex/<alias>/` (tied to the future demo app; defaults documented in
  the README until then).
- Whether to commit `supporting-objects/` install scripts or keep DDL solely in SQLSpec migrations
  (recommend APEXlang owns APEX objects; app schema/data stays in migrations + fixtures).

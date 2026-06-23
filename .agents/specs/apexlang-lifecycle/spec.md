# Flow Spec: apexlang-lifecycle

*Beads: `oracledb-vertexai-apxo.2`*
*Parent PRD: [../apex-ops-console/prd.md](../apex-ops-console/prd.md)*
*Depends on: `apex-runtime-hardening`*
*Status: Planned - implementation-ready*

---

## Context

APEX 26.1 introduces APEXlang as the supported text representation for APEX
applications. SQLcl 26.1 supports APEXlang generation, export, validation, and
import. The repo already has SQLcl installer code, but it does not enforce the
APEXlang-capable version or expose APEXlang lifecycle commands.

Current anchors:

- `tools/oracle/sqlcl_installer.py` downloads `sqlcl-latest.zip`.
- `tools/oracle/sqlcl_installer.py` returns raw `sql -V` output but does not
  enforce SQLcl 26.1+ or APEXlang capability.
- `tools/oracle/cli/apex.py` exposes only install/upgrade/status.
- `src/apex/` is absent.

Official Oracle guidance to use:

- Oracle Skills `apex` domain:
  - `apex/apexlang/references/workflows/apex-generation.md`
  - `apex/apexlang/references/domains/README.md`
- SQLcl 26.1 APEXlang docs:
  - prerequisites require SQLcl 26.1+ and APEX 26.1+
  - SQLcl release notes list APEXlang generate/export/validate/import support
- Official APEXlang layout uses underscores:
  - `shared_components/`
  - `supporting_objects/`

## Requirements

- Add SQLcl version parsing and fail-fast guidance for SQLcl below 26.1.
- Prefer SQLcl 26.1.2+ for this demo because the research target is June 2026.
- Add APEXlang lifecycle wrappers under `manage.py infra apex`:
  - `generate`
  - `export`
  - `validate`
  - `import`
- Create the canonical source root:
  `src/apex/cymbal-coffee-ops/`.
- Use official APEXlang directory names. Do not carry forward older hyphenated
  names from stale drafts.
- Keep APEX app source under `src/apex/`; do not place generated source under
  docs or tooling directories.

## Proposed Changes

### SQLcl Capability Detection

- Extend `SQLclInstaller` with:
  - `parse_version(output: str) -> Version | None`
  - `is_apexlang_capable(minimum: str = "26.1") -> bool`
  - a status object that distinguishes absent SQLcl, old SQLcl, and usable SQLcl
- Tests should mock `sql -V` output and cover version formats seen in SQLcl
  release output.

### APEXlang Service

- Add `tools/oracle/apexlang.py` or `tools/oracle/apex_lang.py` following local
  naming conventions discovered during implementation.
- Provide a small wrapper around SQLcl subprocess execution:
  - resolve `sql`
  - build connection input without logging secrets
  - run APEXlang commands
  - return structured results with stdout/stderr and target paths
- Keep destructive clean/export behavior explicit via flags.

### CLI

- Extend `tools/oracle/cli/apex.py`:
  - `generate --app-name --alias cymbal-coffee-ops`
  - `export --app-id --alias cymbal-coffee-ops`
  - `validate --alias cymbal-coffee-ops`
  - `import --alias cymbal-coffee-ops`
- CLI help should mention SQLcl 26.1.2+ and APEX 26.1+.

### Source Layout

- Add `src/apex/README.md`.
- Create the demo app folder with placeholder structure only when the app
  chapter needs it; this chapter can establish the root and lifecycle contract.

## Implementation Tasks

- [ ] Add SQLcl version parsing and APEXlang capability checks.
- [ ] Add APEXlang command wrapper with subprocess tests.
- [ ] Add `infra apex generate|export|validate|import` Click commands.
- [ ] Add `src/apex/README.md` with official layout names and workflow.
- [ ] Add tests for missing SQLcl, old SQLcl, and usable SQLcl paths.
- [ ] Record the Oracle `apex` skill usage in docs handoff notes.

## Verification

Automated:

```bash
uv run pytest src/tests/unit/tools/oracle/test_sqlcl_installer.py
uv run pytest src/tests/unit/tools/oracle/test_apexlang.py
uv run pytest src/tests/unit/tools/oracle/test_apex_cli.py
make lint
```

Manual, when APEX 26.1 runtime is available:

```bash
uv run python manage.py infra apex validate --alias cymbal-coffee-ops
uv run python manage.py infra apex export --app-id 100 --alias cymbal-coffee-ops
uv run python manage.py infra apex import --alias cymbal-coffee-ops
```

## Done

- SQLcl readiness gates APEXlang work on SQLcl 26.1+ and gives clear install
  guidance.
- APEXlang lifecycle commands exist under `infra apex`.
- Source-controlled APEX work is rooted under `src/apex/`.
- Official Oracle APEXlang skill routing is reflected in the implementation
  notes and docs handoff.

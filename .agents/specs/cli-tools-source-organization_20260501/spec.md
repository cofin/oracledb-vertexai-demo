# Flow: CLI And Tools Source Organization

*Flow ID: `cli-tools-source-organization_20260501`*
*Chapter 5 of [demo-source-organization_20260501](../demo-source-organization_20260501/prd.md)*
*Beads: `oracledb-vertexai-8jt.5`*
*Depends on: `source-organization-contract_20260501`*
*Status: Implemented*

---

## Objective

Keep operator-facing command files declarative while splitting broad helper and
tool modules into responsibility-focused files that a demo reader can navigate.

---

## Primary Files

- `src/app/cli/main.py`
- `src/app/cli/commands/manage.py`
- `src/app/cli/commands/server.py`
- `src/app/cli/_helpers/data_ops.py`
- New focused modules under `src/app/cli/_helpers/`
- `tools/lib/utils.py`
- `tools/cli/*.py`
- `tools/oracle/*.py`
- `tools/oracle/cli/*.py`
- Tests under `src/tests/unit/app/cli/` and `src/tests/integration/tools/oracle/`

---

## Requirements

- `coffee` command modules stay declarative:
  - decorators, parameters, injected services, and one-line helper calls.
  - no local private command implementation functions.
- Split `src/app/cli/_helpers/data_ops.py` by command responsibility. Suggested
  modules:
  - `embeddings.py`
  - `cache.py`
  - `models.py`
  - `database.py`
  - `fixtures.py`
  - optional `tables.py` or `formatting.py` only if needed.
- Either keep `data_ops.py` as a compatibility re-export module or update
  `manage.py` imports directly. Prefer direct focused imports if it stays
  readable.
- Keep `bulk-embed`, `export-fixtures`, `load-fixtures`, `clear-cache`,
  `model-info`, and `run` visible on the `coffee` surface.
- For `tools/oracle` modules, prefer public classes/dataclasses first and move
  command-building, parsing, and formatting helpers below or into private
  siblings only when that reduces scan cost.
- Do not change destructive command behavior. No implementation chapter should
  run destructive Oracle commands unless explicitly requested.

---

## Implementation Plan

1. Extend CLI/tool tests:
   - Keep `src/tests/unit/app/cli/test_surface.py` as the command-surface guard.
   - Add or update tests for new helper module imports if `data_ops.py` becomes
     a compatibility re-export.
   - Update tool integration tests only for import paths, not behavior.
2. Split coffee CLI helpers:
   - Move embedding command helpers from `data_ops.py` into an embeddings module.
   - Move fixture listing/load/export helpers into a fixtures module.
   - Move migration helpers into a database module.
   - Move cache and model-info helpers into small focused modules.
3. Update command imports:
   - Keep `src/app/cli/commands/manage.py` declarative.
   - Ensure `test_public_cli_modules_keep_implementation_helpers_private` still
     passes.
4. Reorganize `tools/lib/utils.py`:
   - Separate env-file generation from command execution and SQLcl/MCP/Gemini
     checks if the split has clear call sites.
   - Preserve current public helper imports or update all consumers in one pass.
5. Reorganize large `tools/oracle` modules:
   - Start with public dataclasses/classes.
   - Move low-level command assembly or parsing helpers into private methods or
     private siblings only when tests cover the public behavior.
6. Run focused verification:
   - `uv run pytest src/tests/unit/app/cli src/tests/integration/tools/oracle -q`
   - `uv run pytest src/tests/unit/app/test_source_organization.py -q`
   - `uv run ruff check src/app/cli tools`

---

## Acceptance Criteria

- `coffee` public command surface is unchanged.
- Command declaration files remain mostly declarative.
- `app.cli._helpers.data_ops` is no longer a 500-line mixed-responsibility file.
- Operational tools remain import-compatible or all consumers are updated.
- Focused CLI/tool tests and Ruff pass.

## Implementation Notes

- Split the former `app.cli._helpers.data_ops` mixed helper module into focused
  `embeddings`, `cache`, `models`, `database`, and `fixtures` modules.
- Kept `data_ops.py` as a small compatibility re-export surface for existing
  imports.
- Updated `app.cli.commands.manage` to import directly from focused helpers
  while keeping the public `coffee` command names unchanged.
- Added a CLI source test that keeps `data_ops.py` small and verifies the
  focused helper imports remain visible.
- Verification: CLI surface tests, Oracle tool integration tests, source
  organization guard, `ruff check src/app/cli tools`, `make lint`, `make test`,
  and `git diff --check`.

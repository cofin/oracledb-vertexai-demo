# Flow: Source Organization Contract

*Flow ID: `source-organization-contract_20260501`*
*Chapter 1 of [demo-source-organization_20260501](../demo-source-organization_20260501/prd.md)*
*Beads: `oracledb-vertexai-8jt.1`*
*Status: Planned*

---

## Objective

Create the guardrails for the source organization refactor before moving code.
The goal is not to enforce arbitrary file size limits. The goal is to make
public demo-facing modules read public-first while allowing private helper
modules and framework-required closures.

---

## Code Analysis Summary

Read and scanned:

- `.agents/patterns.md` - existing rules for domain packages, CLI helpers, and
  tests.
- `src/tests/unit/app/domain/test_layout.py` - existing domain layout guard.
- `src/tests/unit/app/cli/test_surface.py` - existing CLI command helper guard.
- All 89 Python files under `src/app` and `tools` through an AST scan.

Initial hotspots found:

- Public modules with private helper prefixes:
  - `src/app/domain/chat/services/adk.py`
  - `src/app/domain/products/controllers/_vector.py`
  - `src/app/domain/products/services/services.py`
  - `src/app/domain/products/services/maps.py`
  - `src/app/utils/fixtures.py`
  - `src/app/config.py`
- Large broad modules:
  - `src/app/lib/log.py`
  - `src/app/cli/_helpers/data_ops.py`
  - `src/app/utils/domains.py`
  - `tools/lib/utils.py`
  - `tools/oracle/connection.py`
  - `tools/oracle/database.py`
  - `tools/oracle/health.py`
  - `tools/oracle/wallet.py`
  - `tools/oracle/sqlcl_installer.py`
- Framework-required closures to allow intentionally:
  - `ADKRunner._make_tool_factories()` nested ADK tools.
  - `StructlogMiddleware()` nested ASGI middleware.
  - `create_run_command()` nested Granian wrapper.
  - `server/asgi.py:create_app()` lifespan closure.

---

## Requirements

- Add a source organization guard under the existing unit test layout. A good
  target is `src/tests/unit/app/test_source_organization.py` plus a tools-focused
  section or parametrized root list.
- The test must inspect Python files under `src/app` and `tools` using AST, not
  brittle raw string matching.
- The test must classify modules into:
  - public modules: should expose public classes/functions before private helper
    runs.
  - private helper modules: may contain helpers first, but should remain cohesive.
  - explicit exceptions: framework-required closures or module internals with a
    comment explaining why the shape is acceptable.
- The test should be introduced with a temporary allowlist for existing hotspots
  so Chapter 1 can land before all refactors are complete.
- Add a short helper in the test file for finding top-level public/private defs.
  Do not add production code for the audit.
- Record the current hotspot inventory in this spec or a test constant; later
  chapters should remove entries from the allowlist as they fix files.

---

## Implementation Plan

1. Add the source organization test:
   - Create `src/tests/unit/app/test_source_organization.py`.
   - Use `ast.parse()` over `src/app/**/*.py` and `tools/**/*.py`.
   - Build `PUBLIC_MODULES`, `PRIVATE_MODULE_PATTERNS`, and
     `TEMPORARY_HOTSPOT_ALLOWLIST` constants.
   - Assert public modules do not start with more than one top-level private
     function before a public class/function.
   - Assert every allowlist entry points at an existing file and includes a
     reason string.
2. Extend existing tests only when they already own the rule:
   - Keep CLI command declaration checks in `src/tests/unit/app/cli/test_surface.py`.
   - Keep domain package export checks in `src/tests/unit/app/domain/test_layout.py`.
3. Run focused verification:
   - `uv run pytest src/tests/unit/app/test_source_organization.py -q`
   - `uv run pytest src/tests/unit/app/domain/test_layout.py src/tests/unit/app/cli/test_surface.py -q`
4. Update Chapter 1 Beads notes with the exact hotspot inventory and the number
   of files scanned.

---

## Acceptance Criteria

- The source organization guard scans all current Python files under `src/app`
  and `tools`.
- The guard distinguishes public modules from private helper modules.
- Existing hotspots are allowlisted with explicit reasons, not silently ignored.
- No production source files are changed in this chapter.
- Focused tests pass.

# Flow: Source Organization Verification

*Flow ID: `source-organization-verification_20260501`*
*Chapter 6 of [demo-source-organization_20260501](../demo-source-organization_20260501/prd.md)*
*Beads: `oracledb-vertexai-8jt.6`*
*Depends on: `app-core-source-organization_20260501`, `domain-source-organization_20260501`, `adk-runner-source-organization_20260501`, `cli-tools-source-organization_20260501`*
*Status: Planned*

---

## Objective

Close the PRD with a whole-tree audit, remove temporary allowances, capture the
durable source organization rule, and run the repo aggregate gates.

---

## Requirements

- Re-run the source organization guard against all Python files under `src/app`
  and `tools`.
- Remove temporary allowlist entries for files that were fixed in Chapters 2-5.
- Keep only documented framework exceptions:
  - Closure-bound ADK tools if still nested.
  - ASGI/CLI lifespan or wrapper closures required by Litestar/Granian/Click.
  - Private helper modules whose purpose is clear from file/package name.
- Update `.agents/patterns.md` with a concise public-first source organization
  rule only after the refactor proves the convention.
- Do not add broad style guidance that conflicts with existing domain and CLI
  patterns.

---

## Implementation Plan

1. Run source organization audit:
   - `uv run pytest src/tests/unit/app/test_source_organization.py -q`
   - Tighten the allowlist and rerun until it only contains real exceptions.
2. Run focused smoke suites from prior chapters:
   - app core tests
   - domain tests
   - ADK tests
   - CLI/tool tests
3. Update durable guidance:
   - Add a short bullet to `.agents/patterns.md` under Code Style or
     Architecture.
   - The rule should say public demo modules lead with public classes/functions;
     private helpers live below or in focused sibling private modules; command
     modules stay declarative.
4. Run aggregate verification:
   - `make lint`
   - `make test`
   - `git diff --check`
5. Record final Beads notes:
   - Files reorganized.
   - Helper modules added.
   - Allowlist entries left and why.
   - Verification command results.

---

## Acceptance Criteria

- All Python files under `src/app` and `tools` are accounted for by the source
  organization guard.
- Temporary hotspot allowlist entries are gone or explicitly justified.
- `.agents/patterns.md` contains the durable public-first convention.
- `make lint` passes.
- `make test` passes.
- `git diff --check` passes.

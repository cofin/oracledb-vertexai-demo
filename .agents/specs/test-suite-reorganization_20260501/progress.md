# Progress: Test Suite Reorganization

*PRD ID: `test-suite-reorganization_20260501`*
*Status: Implemented*
*Beads epic: `oracledb-vertexai-4d6.9`*

---

## Chapters

- [x] `test-suite-foundation_20260501` - testing architecture, shared helper surface, and layout guard
- [x] `test-suite-unit-layout_20260501` - unit test module-path moves and pure-unit consolidation
- [x] `test-suite-http-layout_20260501` - move `src/tests/api` into integration module paths
- [x] `test-suite-oracle-fixtures_20260501` - session-scoped Oracle schema/data fixtures and mutation cleanup
- [x] `test-suite-consolidation-pass_20260501` - parameterization pass and final verification

## Review Notes

- Draft created from live repository inspection on 2026-05-01.
- Beads epic created: `oracledb-vertexai-4d6.9`.
- Implemented on 2026-05-01.
- Verification passed: `uv run ruff check src/tests`, `uv run pytest src/tests/unit --collect-only`, `uv run pytest src/tests/integration --collect-only`, `make test`, `make lint`, `git diff --check`.

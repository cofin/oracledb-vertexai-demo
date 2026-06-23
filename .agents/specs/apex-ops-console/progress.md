# Progress: APEX Operations Console and Schema Bridge

*PRD ID: `apex-ops-console`*
*Beads: `oracledb-vertexai-apxo`*
*Created: 2026-06-23*

## Status

- [x] External research complete for APEX 26.1, ORDS 26.1.2, SQLcl 26.1.2 APEXlang, official Oracle `apex`/`db` skills, APEX REST Source Catalogs, Antigravity MCP config, MCP Toolbox for Oracle, and Gemini Embedding 2.
- [x] Repository audit complete for current APEX/ORDS runtime, SQLcl installer, legacy Gemini CLI MCP config, Litestar OpenAPI, `litestar-mcp` dependency, product/store/vector services, and missing `src/apex` source tree.
- [x] Beads master epic and six chapter epics created.
- [x] Chapter dependency graph created.
- [x] Master PRD and implementation worksheets drafted.
- [x] Ch1 `apex-runtime-hardening` completed and archived locally on 2026-06-23;
  ORDS version/readiness/lifecycle guidance was elevated to `.agents/patterns.md`.
- [x] Ch2 `apexlang-lifecycle` implemented, focused tests passed, and the spec
  folder was archived locally on 2026-06-23.
- [x] Ch3 `apex-ops-api` closed on 2026-06-23 after adding APEX-safe product,
  store, inventory, recommendation, vector-status, and OpenAPI-status endpoints.
- [x] Ch4 `apex-schema-bridge` closed on 2026-06-23 after adding the filtered
  `/api/apex` OpenAPI export and Antigravity MCP Toolbox config guidance.
- [~] Ch5 `apex-ops-app` has the SQL-backed APEX Operations Console source
  closed; REST Source Catalog import round trip remains blocked in Beads.

## Beads

- Master epic: `oracledb-vertexai-apxo`
- Ch1: `oracledb-vertexai-apxo.1` (`apex-runtime-hardening`) — closed
- Ch2: `oracledb-vertexai-apxo.2` (`apexlang-lifecycle`) — closed; closeout leaf `oracledb-vertexai-apxo.2.1`
- Ch3: `oracledb-vertexai-apxo.3` (`apex-ops-api`) — closed
- Ch4: `oracledb-vertexai-apxo.4` (`apex-schema-bridge`) — closed
- Ch5: `oracledb-vertexai-apxo.5` (`apex-ops-app`) — in progress; `oracledb-vertexai-apxo.5.2` blocked
- Ch6: `oracledb-vertexai-apxo.6` (`apex-demo-verification-docs`) — blocked by Ch5

## Notes

The older `apex-gvenzl-install` PRD remains the infra/APEXlang history of
record. This PRD is the post-research teaching/demo roadmap. Ch1-Ch4 are
closed, Ch5 is partially complete, and Ch6 must wait for the remaining REST
Source Catalog import blocker or an explicit decision to keep the SQL-backed
APEX reports as the demo baseline.

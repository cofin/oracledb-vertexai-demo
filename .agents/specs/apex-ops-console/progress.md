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

## Beads

- Master epic: `oracledb-vertexai-apxo`
- Ch1: `oracledb-vertexai-apxo.1` (`apex-runtime-hardening`)
- Ch2: `oracledb-vertexai-apxo.2` (`apexlang-lifecycle`)
- Ch3: `oracledb-vertexai-apxo.3` (`apex-ops-api`)
- Ch4: `oracledb-vertexai-apxo.4` (`apex-schema-bridge`)
- Ch5: `oracledb-vertexai-apxo.5` (`apex-ops-app`)
- Ch6: `oracledb-vertexai-apxo.6` (`apex-demo-verification-docs`)

## Notes

The older `apex-gvenzl-install` PRD remains the infra/APEXlang history of record.
This PRD is the post-research teaching/demo roadmap and depends on reconciling
the open runtime/tooling gaps from that older work before the app is built.

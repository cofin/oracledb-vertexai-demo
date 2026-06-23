# Flow Spec: apex-schema-bridge

*Beads: `oracledb-vertexai-apxo.4`*
*Parent PRD: [../apex-ops-console/prd.md](../apex-ops-console/prd.md)*
*Depends on: `apex-ops-api`*
*Status: Planned - implementation-ready*

---

## Context

APEX REST Source Catalogs consume OpenAPI documents. MCP clients consume MCP
server configuration. Those are different integration surfaces and should stay
separate in code, docs, and UI language.

Current anchors:

- `src/app/server/core.py` configures the main OpenAPI/Scalar docs.
- `pyproject.toml` already includes `litestar-mcp`.
- `src/app/server/plugins.py` does not initialize `litestar-mcp`.
- `tools/cli/install.py` still has old Gemini CLI logic and writes SQLcl MCP
  configuration to `~/.gemini/settings.json`.
- `tools/lib/utils.py` has helper code for old `~/.gemini/settings.json` MCP
  config.

Official guidance to use:

- APEX REST Source Catalog docs for OpenAPI import/refresh.
- Antigravity MCP docs:
  - IDE custom MCP config: `~/.gemini/config/mcp_config.json`
  - CLI global MCP config: `~/.gemini/antigravity-cli/mcp_config.json`
  - CLI workspace MCP config: `.agents/mcp_config.json`
  - plugin MCP config: plugin-root `mcp_config.json`
- Oracle Skills `db/sqlcl/sqlcl-mcp-server.md` plus Oracle SQLcl MCP docs.
- Google MCP Toolbox Oracle prebuilt config docs.

## Requirements

- Export an APEX-safe OpenAPI subset for `/api/apex/*`, not the full app
  schema.
- Provide a stable local artifact path for the OpenAPI subset.
- Generate clean Antigravity MCP config snippets for:
  - Oracle SQLcl MCP
  - Google MCP Toolbox for Oracle
  - optional Litestar app MCP if enabled later
- Re-add a current installer command such as:
  `uv run python manage.py install mcp-toolbox`.
- Add install/check guidance for official Oracle `apex` and `db` skills.
- Remove touched code paths that write Gemini CLI MCP config to
  `~/.gemini/settings.json`.

## Proposed Changes

### OpenAPI Export

- Add a tool module such as `tools/oracle/openapi_bridge.py` or
  `tools/oracle/apex_catalog.py`.
- Export only operations tagged for APEX or under `/api/apex`.
- Write a deterministic JSON artifact, for example:
  `docs/_static/openapi/apex-catalog.openapi.json` or
  `.agents/generated/apex-catalog.openapi.json`.
- Include title/version/servers metadata that make sense for local APEX import.

### MCP Config Generation

- Replace old Gemini CLI helpers with Antigravity-specific helpers:
  - IDE config writer/checker
  - CLI global config writer/checker
  - workspace config writer/checker
  - print-only mode for docs/lab use
- Default to workspace config for demos:
  `.agents/mcp_config.json`.
- Keep global writes explicit and opt-in.
- Support MCP Toolbox env placeholders without persisting secrets.

### Installer Commands

- Extend `manage.py install` with:
  - `mcp-toolbox` or `mcp`
  - optionally `oracle-skills` for documented install/check of `oracle/skills/apex`
    and `oracle/skills/db`
- Commands should verify availability and emit exact config paths. They should
  not perform Gemini CLI migration.

## Implementation Tasks

- [ ] Add filtered OpenAPI exporter for `/api/apex/*`.
- [ ] Add CLI entry for OpenAPI artifact export.
- [ ] Replace old Gemini MCP config helpers with Antigravity config helpers in
  touched installer paths.
- [ ] Add `manage.py install mcp-toolbox` or equivalent.
- [ ] Add official Oracle Skills install/check guidance.
- [ ] Add tests for config paths, no-secret output, and no writes to
  `~/.gemini/settings.json`.

## Verification

Automated:

```bash
uv run pytest src/tests/unit/tools/test_openapi_bridge.py
uv run pytest src/tests/unit/tools/test_mcp_config.py
uv run pytest src/tests/unit/tools/test_install_mcp_toolbox.py
make lint
```

Manual:

```bash
uv run python manage.py install mcp-toolbox --dry-run
uv run python manage.py install mcp-toolbox --workspace
uv run python manage.py infra apex export-openapi
test -f .agents/mcp_config.json
```

## Done

- APEX gets a filtered OpenAPI catalog artifact.
- Antigravity MCP configs use current paths.
- MCP Toolbox support exists again.
- Oracle SQLcl MCP and Google MCP Toolbox are both demonstrable without mixing
  them with APEX REST Source Catalogs.
- Old Gemini CLI config writes are removed from touched installer paths.


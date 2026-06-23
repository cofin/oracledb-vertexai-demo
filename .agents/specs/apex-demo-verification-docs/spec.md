# Flow Spec: apex-demo-verification-docs

*Beads: `oracledb-vertexai-apxo.6`*
*Parent PRD: [../apex-ops-console/prd.md](../apex-ops-console/prd.md)*
*Depends on: `apex-runtime-hardening`, `apexlang-lifecycle`, `apex-ops-api`, `apex-schema-bridge`, `apex-ops-app`*
*Status: Planned - implementation-ready after dependencies*

---

## Context

The demo needs to be teachable in Sphinx docs and uploadable as a single
markdown lab file. The prior lab/docs/logo work in this branch is unrelated
in-flight work and should be preserved unless the implementation task explicitly
targets it.

Current anchors:

- `docs/index.md` already exists.
- A formal lab markdown file is expected to remain a single-file upload source.
- The user wants a new teaching section:
  `MCP configuration and usage in Antigravity`.

Official guidance to include:

- Oracle APEX 26.1 APEXlang docs.
- Oracle Skills `apex` and `db` domains:
  - `npx skills add oracle/skills/apex`
  - `npx skills add oracle/skills/db`
  - APEXlang generation
  - ORDS
  - SQLcl MCP
  - Oracle vector search
  - container selection
- Antigravity MCP config docs:
  - IDE custom MCP config: `~/.gemini/config/mcp_config.json`
  - CLI global MCP config: `~/.gemini/antigravity-cli/mcp_config.json`
  - CLI workspace MCP config: `.agents/mcp_config.json`
  - plugin-root MCP config: `mcp_config.json`
- Antigravity skill path docs:
  - IDE workspace skills: `<workspace-root>/.agents/skills/<skill-folder>/`
  - IDE global skills: `~/.gemini/antigravity/skills/<skill-folder>/`
  - CLI workspace skills: `.agents/skills/`
  - CLI global skills: `~/.gemini/antigravity-cli/skills/`
- Google MCP Toolbox Oracle docs.

## Requirements

- Add Sphinx docs for:
  - optional APEX 26.1 + ORDS runtime
  - SQLcl APEXlang lifecycle
  - Cymbal Coffee APEX Operations Console
  - APEX REST Source Catalog / OpenAPI bridge
  - MCP configuration and usage in Antigravity
  - official Oracle Skills usage
- Keep the lab upload content as one markdown file.
- Do not split the formal lab into many fragments.
- Use official logos/icons only where license and source are clear; otherwise
  use text headings and simple local styling.
- Add repeatable verification commands for the demo.

## Proposed Docs Structure

- `docs/apex.md`
  - optional APEX runtime
  - APEXlang source lifecycle
  - Operations Console overview
- `docs/mcp-antigravity.md`
  - Antigravity config paths
  - SQLcl MCP
  - MCP Toolbox for Oracle
  - optional app MCP
  - clean config examples, no Gemini CLI migration
  - source-backed Oracle Skills install guidance; no vendored workspace copy
- `docs/reference/brand-assets.md`
  - official-logo sources and usage notes
- `docs/lab.md`
  - single-file formal lab source
- `docs/index.md`
  - include the new APEX and MCP pages

Exact paths should be reconciled with existing in-flight docs work before
editing.

## Smoke Verification Matrix

- APEX media/status:
  `uv run python manage.py infra apex status`
- ORDS readiness:
  `curl -fsS http://localhost:8181/ords/`
- APEX static images:
  `curl -fsS http://localhost:8181/i/`
- SQLcl readiness:
  `uv run python manage.py infra apex validate --alias cymbal-coffee-ops`
- OpenAPI export:
  `uv run python manage.py infra apex export-openapi`
- MCP Toolbox config:
  `uv run python manage.py install mcp-toolbox --dry-run`
- Antigravity workspace config:
  `test -f .agents/mcp_config.json`
- Oracle Skills are not vendored:
  `test ! -d .agents/plugins/oracle-skills`
- Docs:
  `make docs`

## Implementation Tasks

- [ ] Update Sphinx docs index and new pages without disrupting unrelated
  in-flight lab/logo edits.
- [ ] Add the "MCP configuration and usage in Antigravity" section.
- [ ] Add official Oracle Skills section explaining `apex`, `db`, and that ORDS
  lives under `db/ords/`.
- [ ] Include exact Oracle Skills install commands:
  `npx skills add oracle/skills/apex` and
  `npx skills add oracle/skills/db`.
- [ ] Explain that the demo does not add
  `manage.py install oracle-skills --workspace`, does not sync Oracle Skills
  into `.agents/skills/`, and does not create
  `.agents/plugins/oracle-skills/`.
- [ ] Add smoke verification command block and expected outcomes.
- [ ] Ensure the formal lab remains a single markdown file.
- [ ] Run docs build and targeted smoke checks where runtime is available.

## Done

- Sphinx exposes the latest formal lab and the APEX/MCP teaching sections.
- Docs clearly distinguish APEX REST Source Catalogs from MCP.
- Oracle Skills are documented as the official Oracle guidance path with exact
  install commands and no repo-local vendored copy.
- Runtime smoke commands are documented and run where possible.
- The lab content remains uploadable as a single markdown file.

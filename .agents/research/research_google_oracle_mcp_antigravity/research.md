# Research: Google Oracle MCP Toolbox And Antigravity Usage

**Workspace**: `.agents/research/research_google_oracle_mcp_antigravity/`
**Status**: Complete
**Type**: Research + documentation planning
**Date**: 2026-06-22
**Branch**: `fix/product-improve`

This is research only. No application runtime code was changed.

---

## Executive Summary

- Google's MCP Toolbox for Databases is now a current, relevant demo path for
  this repo. The project has been renamed from `genai-toolbox` to
  `mcp-toolbox`, and v1.5.0 was released on 2026-06-18.
- MCP Toolbox supports Oracle through both a prebuilt `oracledb` profile and
  explicit Oracle source configuration.
- Antigravity's current MCP configuration path is user-level:
  `~/.gemini/config/mcp_config.json`. Do not use a project-local `.gemini`
  directory for MCP config.
- Google Cloud also exposes a separate remote MCP endpoint for Google Cloud
  Oracle Database: `https://oracledatabase.googleapis.com/mcp`.
- For teaching, demonstrate two local Antigravity lanes:
  1. SQLcl MCP for Oracle SQLcl-backed database operations.
  2. Google MCP Toolbox Oracle for Google-maintained database tool exposure.

---

## Current External Facts

### MCP Toolbox status

Sources:

- https://github.com/googleapis/mcp-toolbox
- https://github.com/googleapis/mcp-toolbox/releases
- https://mcp-toolbox.dev/documentation/introduction/

Findings:

- The Google repository is now `googleapis/mcp-toolbox`.
- The README states the project was renamed from `genai-toolbox` to
  `mcp-toolbox`.
- Release `v1.5.0` was published on 2026-06-18.
- The README and documentation position MCP Toolbox as usable with modern AI
  clients, including Google Antigravity, Gemini CLI, Claude Code, Codex, and
  other MCP-capable environments.

Implication:

- The previous recommendation to avoid restoring `mcp-toolbox` was too broad.
  It should not return as a Gemini-era default install dependency, but it is now
  justified as an explicit optional install and demo companion.

### MCP Toolbox MCP-client behavior

Source:

- https://mcp-toolbox.dev/documentation/connect-to/mcp-client/

Findings:

- Toolbox can expose tools through MCP transports, including stdio and
  Streamable HTTP.
- The documentation lists support for recent MCP protocol versions, including
  2025-11-25, 2025-06-18, 2025-03-26, and 2024-11-05.
- Toolbox AuthN/AuthZ features are not fully exposed through generic MCP
  clients; Google recommends SDK usage for those advanced features.

Implication:

- For this demo, keep the MCP Toolbox Antigravity example focused on local
  development and inspection tools, not production authorization patterns.

### Oracle prebuilt profile

Sources:

- https://mcp-toolbox.dev/documentation/connect-to/ides/oracle_mcp/
- https://mcp-toolbox.dev/integrations/oracle/prebuilt-configs/oracle/

Findings:

- Oracle prebuilt support requires MCP Toolbox v0.26.0 or newer; the current
  docs show v1.5.0 binary download URLs.
- The prebuilt profile value is `oracledb`.
- A local MCP client can launch Toolbox with:

```json
{
  "mcpServers": {
    "oracle-toolbox": {
      "command": "/absolute/path/to/toolbox",
      "args": ["--prebuilt", "oracledb", "--stdio"],
      "env": {
        "ORACLE_CONNECTION_STRING": "localhost:1521/FREEPDB1",
        "ORACLE_USERNAME": "app",
        "ORACLE_PASSWORD": "${ORACLE_PASSWORD}"
      }
    }
  }
}
```

- Supported Oracle environment variables include:
  - `ORACLE_CONNECTION_STRING`
  - `ORACLE_USERNAME`
  - `ORACLE_PASSWORD`
  - `ORACLE_WALLET`
  - `ORACLE_USE_OCI`
- The Oracle prebuilt tools include database inspection and SQL execution
  capabilities such as `execute_sql`, `list_tables`, `list_active_sessions`,
  `get_query_plan`, `list_top_sql_by_resource`, `list_tablespace_usage`, and
  `list_invalid_objects`.
- Google labels prebuilt tools as pre-1.0, so tool names and behavior may still
  change.

Implication:

- Track the tool version in docs and examples.
- Use absolute binary paths in Antigravity config because desktop/agent
  processes may not inherit the shell `PATH`.
- Do not commit real passwords to `.agents/` or `docs/`.

### Oracle explicit source

Source:

- https://mcp-toolbox.dev/integrations/oracle/source/

Findings:

- MCP Toolbox supports Oracle source configuration.
- Default `useOCI: false` uses a pure Go driver and does not require local
  Oracle client software, but it does not support advanced Wallet or Kerberos
  scenarios.
- `useOCI: true` uses the OCI/godror driver, supports Wallet and Kerberos, and
  requires Oracle Instant Client.
- Connection configuration can use host/port/service name, a full connection
  string, or TNS alias.
- The source tools include `list_tables`, `oracle-execute-sql`, and
  `oracle-sql`.

Implication:

- For the Cymbal Coffee workshop, start with the prebuilt profile for the
  quickest demonstration. Use explicit source config later when the lab needs
  a curated, least-privilege tool list.

### Google Cloud Oracle Database remote MCP

Sources:

- https://docs.cloud.google.com/oracle/database/docs/reference/mcp
- https://docs.cloud.google.com/mcp/configure-mcp-ai-application
- https://docs.cloud.google.com/mcp/authenticate-mcp
- https://docs.cloud.google.com/mcp/enable-disable-mcp-servers

Findings:

- Google Cloud Oracle Database has a remote MCP endpoint:
  `https://oracledatabase.googleapis.com/mcp`.
- Google Cloud MCP configuration requires the target product API to be enabled.
- Tool callers need the `roles/mcp.toolUser` role, which includes
  `mcp.tools.call`.
- Authentication uses Application Default Credentials. Google documents
  `gcloud auth application-default login`, with token refresh handled by
  supported clients such as Antigravity and Gemini CLI.
- Generic MCP AI application config uses a server name, endpoint URL, HTTP
  transport, auth, and OAuth scopes.

Implication:

- This is a separate teaching lane from local Oracle Free / Cymbal Coffee.
  Demonstrate it as a Google Cloud MCP concept, not as the default local lab
  prerequisite.

---

## Antigravity Teaching Section Plan

Proposed Sphinx section title:

```text
MCP Configuration And Usage In Antigravity
```

Teaching objectives:

- Explain what MCP adds to the Cymbal Coffee demo.
- Show where Antigravity reads MCP configuration.
- Contrast SQLcl MCP and Google MCP Toolbox Oracle.
- Keep the examples clean: no Gemini CLI migration, no legacy
  `~/.gemini/settings.json`, no project-local `.gemini` config.
- Show local-only safety defaults and credential handling.

Recommended section outline:

1. Antigravity MCP config paths.
2. SQLcl MCP server for the app schema.
3. Google MCP Toolbox Oracle prebuilt server.
4. Optional Google Cloud Oracle Database remote MCP endpoint.
5. Safety checklist: least-privilege user, no production credentials, inspect
   generated SQL, and keep secrets out of git.

---

## Visual Reference And Icon Recommendations

Sources:

- https://sphinx-design.readthedocs.io/en/latest/badges_buttons.html
- https://sphinx-immaterial.readthedocs.io/en/latest/inline_icons.html
- https://github.com/primer/octicons
- https://developers.google.com/fonts/docs/material_symbols
- https://cloud.google.com/icons
- https://github.com/litestar-org/branding
- https://www.oracle.com/legal/logos/
- https://www.oracle.com/legal/trademarks/

Findings:

- The repo already uses Sphinx Immaterial and Sphinx Design, so Octicon and
  Material icon roles are the lowest-friction visual layer.
- GitHub Octicons are MIT licensed.
- Google Material Symbols are Apache-2.0 licensed.
- Google Cloud provides an official icon library for architecture diagrams and
  technical documentation.
- Oracle logo usage is constrained by third-party logo and trademark
  guidelines. Do not use Oracle logos as generic page decoration unless an
  approved use case and asset are confirmed.

Recommended doc treatment:

- Use inline Octicons on landing cards and MCP comparison cards.
- Use Mermaid diagrams for architecture flow instead of downloaded vendor
  diagrams unless a formal architecture diagram needs official Google Cloud
  product icons.
- Prefer generic database/server/terminal icons for Oracle concepts in docs.
- Keep the existing Cymbal Coffee SVG brand assets for project identity.
- Add external references in the MCP teaching page so future asset decisions are
  traceable.

Fetched asset inventory:

- `docs/_static/logos/oracle-logo.svg` from Oracle's hosted SVG asset:
  `https://www.oracle.com/a/ocom/img/oracle-logo.svg`
- `docs/_static/logos/google-cloud-logo-fullcolor.svg` from the Google Cloud
  site asset:
  `https://www.gstatic.com/cgc/google-cloud-logo-fullcolor.svg`
- Google Cloud product icons from
  `https://services.google.com/fh/files/misc/core-products-icons.zip`:
  - `google-cloud-vertex-ai.svg`
  - `google-cloud-bigquery.svg`
  - `google-cloud-compute-engine.svg`
  - `google-cloud-cloud-run.svg`
- Google Cloud category icons from
  `https://services.google.com/fh/files/misc/category-icons.zip`:
  - `google-cloud-databases.svg`
  - `google-cloud-ai-ml.svg`
  - `google-cloud-agents.svg`
  - `google-cloud-maps-geospatial.svg`
- `docs/_static/logos/antigravity-logo.png` from the official Antigravity site:
  `https://antigravity.google/assets/image/antigravity-logo.png`
- `docs/_static/logos/litestar-logo.svg` from the official Litestar branding
  repository standalone badge SVG:
  `https://github.com/litestar-org/branding/blob/main/assets/Branding%20-%20SVG%20-%20Transparent/Badge%20-%20Blue%20and%20Yellow.svg`
- `docs/_static/logos/mcp-toolbox-logo.png` from the first-party
  `googleapis/mcp-toolbox` repository:
  `https://github.com/googleapis/mcp-toolbox/blob/main/logo.png`

---

## Recommended Repo Enhancements

Add optional installer support:

```bash
uv run python manage.py install mcp-toolbox --version 1.5.0
```

Add explicit config support:

```bash
uv run python manage.py install mcp sqlcl --client antigravity
uv run python manage.py install mcp oracle-toolbox --client antigravity
uv run python manage.py install mcp status
```

Suggested behavior:

- `mcp-toolbox` downloads a pinned or user-selected Toolbox binary into a local
  tool path.
- `mcp sqlcl` writes or previews only the `sqlcl` MCP entry.
- `mcp oracle-toolbox` writes or previews only the `oracle-toolbox` MCP entry.
- `mcp status` reports which MCP servers are configured, which executable paths
  are valid, and whether credentials are missing.
- All write operations preserve unrelated `mcpServers` entries.
- No command reads or migrates legacy Gemini CLI config.

---

## Open Questions For Implementation

- Should `mcp-toolbox` install into `~/.local/bin/toolbox` or a repo-managed
  tools directory?
- Should the Antigravity config writer support a `--scope project` mode that
  emits a template under `.agents/examples/antigravity/` without secrets?
- Should Oracle Toolbox use the prebuilt profile for the first lab and move to
  explicit `tools.yaml` once the teaching flow stabilizes?
- Should docs pin the Toolbox binary version to `1.5.0` or document "latest
  verified" with a refresh date?

Recommended default:

- Install the binary explicitly, generate user-level Antigravity config only
  when requested, and keep committed examples secret-free.

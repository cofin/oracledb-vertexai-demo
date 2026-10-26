# MCP Configuration And Usage In Antigravity

Antigravity can use MCP servers to give the assistant controlled access to the
same Oracle database used by Cymbal Coffee. For this workshop, keep the setup
clean: configure current Antigravity MCP files directly, avoid legacy Gemini CLI
migration, and never commit credentials.

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} {octicon}`terminal;1.2em` SQLcl MCP

Use Oracle SQLcl as the direct MCP bridge for local Oracle SQL operations
against the demo schema.
:::

:::{grid-item-card} {octicon}`database;1.2em` MCP Toolbox Oracle

Use Google's MCP Toolbox Oracle prebuilt profile for database inspection and
toolbox-managed SQL execution.
:::

:::{grid-item-card} {octicon}`cloud;1.2em` Google Cloud Oracle MCP

Use the Google Cloud Oracle Database remote MCP endpoint only when teaching the
managed Google Cloud MCP flow.
:::

:::{grid-item-card} {octicon}`shield-check;1.2em` Safety posture

Use least-privilege demo credentials, preview generated config, and keep all
secrets outside tracked files.
:::

::::

## Config Location

Antigravity IDE and Antigravity CLI (`agy`) read MCP server entries from a
workspace-scoped file or an explicit global user-level file:

```text
.agents/mcp_config.json
~/.gemini/config/mcp_config.json
~/.gemini/antigravity-cli/mcp_config.json
```

On Windows the global IDE file is `%USERPROFILE%\.gemini\config\mcp_config.json`.
To manage servers in the IDE UI, open **Settings > Customizations > Installed
MCP Servers**. Keep secret-free workspace templates under `.agents/` or `docs/`,
and store credentials in environment variables or Secret Manager rather than
tracked files.

## SQLcl MCP

SQLcl MCP is the shortest path from Antigravity to the local Oracle 26ai demo
schema. Against the default managed `adb-free:latest-26ai` container
(`cymbal-adb-free`, serving Oracle APEX 26.1.5 and ORDS 26.3 at
`https://localhost:8443/ords/apex` for workspace `COFFEE`), connect as the
app-scoped user `APP` over service `myatp_low` with the exported TLS wallet in
`.envs/tns` rather than `ADMIN`, `SYS`, or `SYSTEM`.

```json
{
  "mcpServers": {
    "sqlcl": {
      "command": "sql",
      "args": ["-mcp"]
    }
  }
}
```

Ensure `~/.local/bin` is on `PATH` (or supply an absolute path to `sql` if your
desktop environment starts with a minimal `PATH`).

## MCP Toolbox Oracle

Google's MCP Toolbox runs a prebuilt Oracle server configured through
environment placeholders so credentials never sit in `mcp_config.json`:

```json
{
  "mcpServers": {
    "oracle-toolbox": {
      "command": "toolbox",
      "args": ["--prebuilt", "oracledb", "--stdio"],
      "env": {
        "ORACLE_CONNECTION_STRING": "${ORACLE_CONNECTION_STRING}",
        "ORACLE_USERNAME": "${ORACLE_USERNAME}",
        "ORACLE_PASSWORD": "${ORACLE_PASSWORD}",
        "ORACLE_WALLET": "${ORACLE_WALLET}",
        "ORACLE_USE_OCI": "${ORACLE_USE_OCI}"
      }
    }
  }
}
```

For the default managed `adb-free:latest-26ai` container (`cymbal-adb-free`),
point `ORACLE_USERNAME` to `app`, `ORACLE_CONNECTION_STRING` to `myatp_low`, and
`ORACLE_WALLET` to `.envs/tns`. For an external non-wallet Oracle instance, set
`ORACLE_CONNECTION_STRING` to `host:1521/service_name` and leave
`ORACLE_WALLET` unset. The prebuilt profile avoids maintaining a custom
`tools.yaml` before the workshop flow needs a curated tool list.

## Application MCP And A2A Endpoints

Alongside database-level MCP servers, the running Cymbal Coffee Litestar app
(`http://localhost:8000`) exposes its own `LitestarMCP` `0.15` and `LitestarA2A`
protocol endpoints:

- `http://localhost:8000/mcp` — HTTP MCP server exposing catalog, Hybrid RRF
  search, store inventory, `CoffeePromptController`
  (`src/app/domain/ai/mcp/_prompts.py`), and `CoffeeSkillController`
  (`src/app/domain/ai/mcp/_skills.py`).
- `http://localhost:8000/a2a` and
  `http://localhost:8000/.well-known/agent-card.json` — Agent-to-Agent endpoint
  and discovery card (`src/app/domain/ai/a2a/_card.py`,
  `src/app/domain/ai/a2a/_executor.py`).

When `MCP_API_KEY` is set in `.env`, both `/mcp` and `/a2a` require the matching
`X-API-Key` or `Authorization: Bearer` header (`src/app/lib/security.py`).

## Google Cloud Oracle MCP

Google Cloud Oracle Database also exposes a remote MCP endpoint:

```text
https://oracledatabase.googleapis.com/mcp
```

Use this as a separate managed-cloud example. It is a remote HTTP MCP server, so
register it with `serverUrl` (and auth headers) rather than `command`/`args`. It
requires the Oracle Database@Google Cloud API (`oracledatabase.googleapis.com`)
to be enabled, OAuth 2.0 credentials over IAM (Application Default Credentials
satisfy this), and a principal granted the MCP Tool User role
(`roles/mcp.toolUser`) plus the resource roles for the databases it touches.

## Repository CLI Installer

Use the `manage.py install` commands (`tools/cli/install.py`) to install SQLcl
and preview or write the secret-free Antigravity MCP configuration:

```shell
uv run python manage.py install list
uv run python manage.py install sqlcl
uv run python manage.py install mcp-toolbox --dry-run
uv run python manage.py install mcp-toolbox --workspace
uv run python manage.py install mcp-toolbox --ide
uv run python manage.py install mcp-toolbox --cli-global
```

`write_antigravity_mcp_config` (`tools/lib/utils.py`) merges the `sqlcl` and
`oracle-toolbox` entries into `mcpServers`, preserves unrelated MCP servers, and
never reads legacy `~/.gemini/settings.json`.

## Visual References

Use built-in documentation icons first:

- Sphinx Design supports Octicon and Material icon roles for inline SVG icons.
- Sphinx Immaterial supports bundled icon names and custom SVG icon paths.
- GitHub Octicons are MIT licensed.
- Google Material Symbols are Apache-2.0 licensed.

Use official product artwork sparingly:

- Google Cloud provides an official icon library for architecture diagrams and
  technical documentation.
- Oracle logo usage is governed by Oracle's third-party logo and trademark
  guidelines. Prefer generic database icons in this documentation unless an
  approved Oracle asset is already part of the project.

Useful references:

- [Sphinx Design inline icons](https://sphinx-design.readthedocs.io/en/latest/badges_buttons.html#inline-icons)
- [Sphinx Immaterial inline icons](https://sphinx-immaterial.readthedocs.io/en/latest/inline_icons.html)
- [GitHub Octicons](https://github.com/primer/octicons)
- [Google Material Symbols](https://developers.google.com/fonts/docs/material_symbols)
- [Google Cloud icon library](https://cloud.google.com/icons)
- [Oracle logo usage guidelines](https://www.oracle.com/legal/logos/)
- [Local official asset inventory](reference/brand-assets.md)

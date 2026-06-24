# Research: Restore SQLcl MCP Tooling for Antigravity CLI

**Workspace**: `.agents/research/research_sqlcl_mcp_antigravity_revival/`
**Status**: Complete
**Type**: Historical research + integration planning
**Date**: 2026-06-22
**Branch**: `fix/product-improve`

This is research only. No application code was changed.

---

## Executive Summary

- The original workflow installed Gemini CLI and configured MCP servers for SQLcl, sequential-thinking, and Context7 in `~/.gemini/settings.json`.
- That exact flow should not be restored. Google has transitioned Gemini CLI consumer/free-tier usage to Antigravity CLI, and Antigravity uses a different MCP configuration path.
- The repo still contains Gemini-specific SQLcl MCP helpers in `tools/lib/utils.py` and `tools/cli/install.py`, but they target the old `~/.gemini/settings.json` shape and only run when a `gemini` executable is present.
- Current Antigravity docs and codelabs use a central MCP config file at `~/.gemini/config/mcp_config.json`. Local `agy` is installed and supports `plugin import`, `plugin install`, `plugin validate`, and related plugin commands.
- The restoration should be a clean **Antigravity MCP config layer**. Keep the SQLcl saved connection setup, but replace `configure_gemini_mcp_sqlcl()` with an Antigravity-specific `configure_sqlcl_mcp()` that writes only current config.
- Do not re-add `manage.py install gemini-cli`. Revisit `manage.py install mcp-toolbox` as an explicit optional installer because Google's current MCP Toolbox for Databases now has an Oracle prebuilt config and is a valid demo companion to SQLcl MCP. It should not be part of baseline `install all`.

---

## Current External Facts

### Gemini CLI transition

Source: https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/

Google's 2026-05-19 transition announcement says:

- Gemini CLI is being unified into Google Antigravity and Antigravity CLI.
- Antigravity CLI keeps key Gemini CLI concepts: Agent Skills, Hooks, Subagents, and Extensions, now as Antigravity plugins.
- On 2026-06-18, Gemini CLI and Gemini Code Assist IDE extensions stop serving requests for Google AI Pro/Ultra and free individual usage. Enterprise and API-key paths remain different.

Implication:

- Any repo-owned helper that assumes `gemini` is the active terminal agent is stale for the default individual developer path.
- Do not read, import, or migrate the old Gemini config. The restored repo command should generate clean Antigravity config from current `.env` and current SQLcl discovery.

### Antigravity MCP configuration

Sources:

- Antigravity MCP codelab: https://codelabs.developers.google.com/developer-knowledge-mcp-antigravity
- Antigravity MCP docs: https://antigravity.google/docs/mcp
- Antigravity CLI plugins docs: https://antigravity.google/docs/cli-plugins
- Antigravity plugins docs: https://antigravity.google/docs/plugins

Findings:

- Antigravity 2.0, IDE, and CLI share central MCP configuration at `~/.gemini/config/mcp_config.json`.
- MCP server entries use an `mcpServers` object. Remote servers use `serverUrl`; local servers use command/args style.
- The CLI verifies MCP setup from inside `agy` with `/mcp`.
- Local `agy --help` reports version `1.0.8` in this environment.
- Local `agy plugin --help` exposes `list`, `import [source]`, `install`, `uninstall`, `enable`, `disable`, `validate`, and `link`.
- Local `agy plugin list` shows existing imports from `gemini-cli` for Flow, Litestar, and Superpowers, proving the import path exists locally.

Implication:

- The repo should write `~/.gemini/config/mcp_config.json`, not `~/.gemini/settings.json`, for Antigravity.
- `agy plugin import gemini` exists as a local tool, but this repo should not use it for SQLcl setup. SQLcl is project/database-specific and should be generated cleanly from the current `.env`.

### SQLcl MCP

Sources:

- SQLcl 26.1.2 release notes: https://www.oracle.com/tools/sqlcl/sqlcl-relnotes-26.1.2.html
- Oracle SQLcl MCP Server docs: https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.4/sqcug/using-oracle-sqlcl-mcp-server.html
- SQLcl MCP startup/client config docs: https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.2/sqcug/starting-and-managing-sqlcl-mcp-server.html

Findings:

- SQLcl 26.1.2 release notes call out APEXlang support and note that SQLcl MCP startup now defaults to unrestricted, whereas it was previously restriction level 4.
- Oracle documents SQLcl MCP as an MCP server that enables AI applications to perform operations, create reports, and run queries against Oracle Database.
- Oracle's client examples configure MCP clients with:

```json
{
  "mcpServers": {
    "sqlcl": {
      "command": "PATH/bin/sql",
      "args": ["-mcp"]
    }
  }
}
```

- Oracle explicitly warns against broad production database access, recommends minimum permissions, and notes built-in monitoring through `DBTOOLS$MCP_LOG`, `V$SESSION` metadata, and LLM-generated query markers.

Implication:

- SQLcl MCP remains a valid integration target.
- Because SQLcl 26.1.2 changed default restriction behavior, this repo should choose and document an explicit safety posture instead of relying on default MCP restrict behavior.
- The saved SQLcl connection should use a least-privileged local/demo account. For this repo, that means the existing `app`-scoped demo user, not SYS/SYSTEM.

---

## Git History Findings

### Original behavior

Commit trail:

- `1d68651 fix: updated tool installer`
- `094da5a feat: Refactor Oracle CLI into modular command groups`
- `03f95ef fix: include missing lib directory and updated agents (#13)`

The old docs included:

- `docs/guides/gemini-mcp-integration.md`
- `docs/guides/sqlcl-usage-guide.md`

The old Gemini guide described this flow:

- `python3 manage.py install gemini-cli`
- install `@google/gemini-cli` globally with npm,
- detect SQLcl if installed,
- configure SQLcl MCP,
- optionally configure sequential-thinking and Context7,
- write `~/.gemini/settings.json`.

The old SQLcl guide documented:

- `sql -mcp`,
- saved SQLcl connections using `conn -save ... -savepwd ...`,
- example MCP client configuration for Gemini CLI, Claude Desktop, and Cline,
- security guidance for least privilege, non-production use, and monitoring.

The historical `tools/cli/install.py` at `094da5a` had:

- `install uv`,
- `install sqlcl`,
- `install gemini-cli`,
- `install mcp-toolbox`,
- `_configure_missing_mcp_extensions()`,
- automatic SQLcl MCP configuration when `gemini` was detected,
- `configure_gemini_mcp_extensions(interactive=True)` for sequential-thinking and Context7.

Commit `03f95ef` added the missing `tools/lib/utils.py` implementation with:

- `is_mcp_server_configured()`,
- `is_sqlcl_connection_saved()`,
- `migrate_sqlcl_connection()`,
- `configure_sqlcl_connection_with_password()`,
- `configure_gemini_mcp_sqlcl()`,
- `configure_gemini_mcp_extensions()`.

### Intentional removal

The local plan `.agents/plans/installation-simplification.md` states the goal plainly:

- centralize base tool installation in Makefile,
- remove `gemini-cli` and `mcp-toolbox` commands from `tools/cli/install.py`,
- remove `uv` install from `tools/cli/install.py`,
- keep SQLcl as the install group focus,
- remove general MCP extension helpers,
- retain/restore SQLcl-specific MCP functions.

Commit `68eeb3c feat: Q1 2026 Demos (#17)` applied that direction:

- removed `gemini-cli`, `mcp-toolbox`, and `uv` install commands,
- removed `configure_gemini_mcp_extensions`,
- kept SQLcl-focused install behavior,
- deleted the committed `.gemini` directory and moved knowledge into `.agents`.

Commit `adb7aba` later removed the `mcp_demo` to `cymbal_coffee` saved-connection migration as legacy cleanup.

### Current branch state

Current branch `fix/product-improve` has only two commits on top of `main`:

- `63a3c74 fix(chat): guard dynamic product rag responses`
- `b61241d fix(deps): update apexcharts to version 5.15.2 and ruff-pre-commit to v0.15.18`

So the Gemini/MCP tooling is not a new regression on this branch tip; it is legacy behavior from earlier shared history.

Current live files:

- `tools/cli/install.py` still imports `configure_gemini_mcp_sqlcl` and checks for `gemini`.
- `tools/cli/install.py` still auto-configures SQLcl MCP only when `shutil.which("gemini")` is true.
- `tools/lib/utils.py` still hard-codes `~/.gemini/settings.json`.
- `tools/oracle/cli/sqlcl.py` provides a separate SQLcl install/verify/uninstall group, but it is not where the Gemini-specific MCP code lives.

This creates an awkward halfway state:

- broad Gemini CLI installer is gone, correctly,
- SQLcl MCP helpers remain, correctly in spirit,
- but the helpers are tied to the old Gemini client and old config file.

---

## Recommended Restoration

### Do not restore these

- Do not restore `manage.py install gemini-cli`.
- Do not restore `npm install -g @google/gemini-cli`.
- Do not restore the old `configure_gemini_mcp_extensions()` as a default install flow.
- Do not restore the old `mcp-toolbox` command as a core prerequisite or Gemini-era extension install. Do restore an explicit optional `manage.py install mcp-toolbox` style command if the next Flow includes the Google MCP Toolbox Oracle demo.

### Restore the capability under a new abstraction

Add a small MCP client configuration module, for example:

```text
tools/mcp/
  __init__.py
  client_config.py
  sqlcl.py
```

Suggested responsibilities:

- `client_config.py`
  - JSON load/write helpers that preserve unrelated current Antigravity keys.
  - a single first-class target:
    - `antigravity`: `~/.gemini/config/mcp_config.json`
  - optional future targets only when actively needed, such as Claude Desktop or Cline.
  - no legacy Gemini target.
  - `is_mcp_server_configured(server_name)`
  - `configure_mcp_server(server_name, server_config)`

- `sqlcl.py`
  - find SQLcl executable through `SQLclInstaller` or `shutil.which("sql")`,
  - prefer absolute SQLcl path in MCP config,
  - call existing saved connection setup,
  - emit SQLcl MCP server config:

```json
{
  "mcpServers": {
    "sqlcl": {
      "command": "/absolute/path/to/sql",
      "args": ["-mcp"]
    }
  }
}
```

### Add explicit CLI commands

Recommended command shape:

```bash
uv run python manage.py install mcp sqlcl --connection-name cymbal_coffee
uv run python manage.py install mcp status
```

Why separate from `install sqlcl`:

- Installing SQLcl and mutating an agent client's global config are different operations.
- Antigravity may already be installed, imported, and configured independently.
- A non-mutating `status` command can tell users what will change before writing `~/.gemini/config/mcp_config.json`.

Still keep a convenience prompt in `install sqlcl`:

- If `agy` is present and no Antigravity SQLcl MCP server exists, print:

```text
SQLcl can be exposed to Antigravity via MCP.
Run: uv run python manage.py install mcp sqlcl --client antigravity
```

Avoid auto-writing global agent config from a plain SQLcl install unless the user passes an explicit flag.

### Clean config policy

Do not add migration support.

Behavior:

- writes only `~/.gemini/config/mcp_config.json`,
- builds the SQLcl MCP server entry from current SQLcl discovery and current `.env`,
- preserves unrelated existing Antigravity MCP entries in the same file,
- replaces the repo-owned `sqlcl` entry deterministically when requested,
- does not read `~/.gemini/settings.json`,
- does not call `agy plugin import gemini`,
- does not create compatibility aliases for old connection names.

### Add plugin validation support, but do not make it required

Local `agy plugin validate [path]` exists. Use it only if this repo later creates a real Antigravity plugin bundle.

Near-term:

- use central MCP config writer only,
- no repo plugin needed.

Future plugin option:

- package a Cymbal Coffee Antigravity plugin that includes:
  - SQLcl MCP server config guidance,
  - project rules,
  - APEXlang skills,
  - safe prompts for Oracle vector search and APEX app development.

That should be its own Flow because plugin schema and distribution deserve separate validation.

### Add optional MCP Toolbox install support

New research on 2026-06-22 changes the earlier recommendation. Google's
current MCP Toolbox for Databases is no longer just a historical Gemini-era
extra for this repo: it has an Oracle prebuilt profile, current Antigravity
positioning, and v1.5.0 binaries published 2026-06-18.

Recommended command surface:

```bash
uv run python manage.py install mcp-toolbox --version 1.5.0
uv run python manage.py install mcp oracle-toolbox --client antigravity --scope project
```

Responsibilities:

- `install mcp-toolbox` downloads/verifies the Toolbox binary into the same
  local tool convention as SQLcl, for example `~/.local/bin/toolbox`.
- It is explicit and optional; `install all` should continue to focus on
  project prerequisites and SQLcl.
- It should not write Antigravity config by default. Configuration belongs in
  a separate `install mcp ...` command with dry-run/status support.
- Antigravity config should use absolute executable paths because GUI/agent
  environments often do not inherit the developer's shell `PATH`.
- Oracle credentials must not be committed under `.agents/`; generated local
  config should use environment placeholders or write only to user-local config
  when secrets are needed.

This keeps the Q1 simplification principle intact while adding the now-relevant
Google Oracle MCP demo path.

---

## Safety Model

SQLcl MCP can run database operations through an LLM client. The repo should make that explicit.

Recommended defaults:

- local/development only,
- `app` user connection, not SYS/SYSTEM,
- saved connection named `cymbal_coffee`,
- no production wallet auto-discovery for MCP unless explicitly requested,
- no destructive database prompts in docs,
- include instructions to inspect `DBTOOLS$MCP_LOG`.

Because SQLcl 26.1.2 changed MCP startup defaults to unrestricted, decide whether to pass an explicit restrict flag after verifying the current SQLcl CLI flag syntax locally. Do not assume old restriction-level behavior.

---

## Test Plan for Implementation

Unit tests:

- JSON config writer preserves unrelated keys.
- Antigravity target writes `~/.gemini/config/mcp_config.json` by default, with HOME patched to a temp dir.
- `configure_sqlcl_mcp()` writes absolute SQLcl command path.
- Existing server entries are idempotent and not duplicated.
- Existing unrelated Antigravity MCP servers are preserved.
- The repo-owned `sqlcl` entry is overwritten deterministically when `--force` or an explicit update flag is used.

CLI tests:

- `manage.py install mcp --help` shows `sqlcl` and `status`.
- `manage.py install mcp sqlcl --client antigravity --dry-run` prints intended file and server.
- With patched `shutil.which("agy")`, `install sqlcl` suggests the MCP command but does not mutate config unless explicitly requested.
- Missing SQLcl produces actionable guidance.
- Missing `.env` produces actionable guidance for saved connection setup.

Manual validation:

```bash
uv run python manage.py install mcp sqlcl --client antigravity --dry-run
uv run python manage.py install mcp sqlcl --client antigravity
python3 -m json.tool ~/.gemini/config/mcp_config.json
agy
/mcp
```

Repo gates:

```bash
make lint
make test
```

---

## Proposed Flow Scope

Create a new Flow rather than folding this into APEX install:

**Name**: `sqlcl-mcp-antigravity`

Scope:

- Restore SQLcl MCP setup for the current Antigravity CLI era.
- Add target-aware MCP config helpers.
- Add an explicit `manage.py install mcp ...` command surface.
- Remove or rename Gemini-specific helper functions instead of carrying compatibility paths.
- Do not install Antigravity itself.
- Do not create an Antigravity plugin bundle yet.

Acceptance:

- A developer can run one repo command to configure SQLcl MCP for Antigravity.
- The command writes `~/.gemini/config/mcp_config.json` and preserves existing MCP servers.
- The SQLcl saved connection uses the current `.env` database settings.
- The docs no longer point users to Gemini CLI as the default.
- Tests cover config paths, idempotence, dry-run behavior, clean overwrite behavior, and unrelated-entry preservation.

---

## Open Decision

Recommended answer:

- Make **Antigravity central MCP config** the only restoration target now.
- Delete or rename **Gemini-specific helper names** so the code no longer implies old-client support.
- Defer **Antigravity plugin bundle** until SQLcl MCP config works and the APEXlang app/source flow is stable.

Question for planning:

Should this be its own Flow (`sqlcl-mcp-antigravity`) rather than being bundled into the APEX 26/APEXlang Flow?

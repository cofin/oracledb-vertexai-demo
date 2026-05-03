# Plan: Installation Simplification & Gemini/MCP Removal

The goal is to centralize tool installation (`uv`, `bun`) in the `Makefile` and remove all Gemini/MCP-related logic (except SQLcl MCP) and commands from `manage.py` and the `tools/` directory.

## 1. Summary of Changes

### 1.1 `Makefile` (Centralization)
- Keep `install-uv` and `install-bun` targets.
- Ensure they are the primary installers for these tools.

### 1.2 `manage.py` & `tools/cli/` (Simplification)
- **Remove** `gemini-cli` and `mcp-toolbox` commands from `tools/cli/install.py`.
- **Remove** `uv` installation command from `tools/cli/install.py`.
- **Update** `install all` command to focus on `sqlcl`.

### 1.3 `tools/lib/utils.py` (Selective Stripping)
- **Remove** `configure_gemini_mcp_extensions`.
- **Retain/Restore** SQLcl MCP functions:
    - `is_mcp_server_configured`
    - `configure_gemini_mcp_sqlcl`
    - `is_sqlcl_connection_saved`
    - `configure_sqlcl_connection_with_password`
    - `migrate_sqlcl_connection`

### 1.4 Documentation Removal
- **Delete** `tools/MIGRATION_GUIDE.md`.

## 2. Implementation Steps

### Step 1: Delete Documentation
- Remove `tools/MIGRATION_GUIDE.md`.

### Step 2: Refactor `tools/lib/utils.py`
- Strip general MCP extension functions.
- Restore SQLcl specific MCP functions (previously removed).

### Step 3: Refactor `tools/cli/install.py`
- Remove `uv`, `gemini-cli`, and `mcp-toolbox` installation logic.

### Step 4: Refactor `tools/cli/__init__.py`
- Clean up exports.

## 3. Verification Plan
- `python manage.py install --help`: Check for removal of commands.
- `make install-uv`: Verify functionality.
- `uv run mypy tools manage.py`: Verify types.

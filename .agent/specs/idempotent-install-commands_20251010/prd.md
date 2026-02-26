# Idempotent Installation Commands & Cross-Configuration

## Overview

Make all installation commands in `manage.py` and `Makefile` idempotent (safe to run multiple times) and implement smart cross-configuration between tools (gemini-cli <-> sqlcl). Additionally, rename the default SQLcl connection from "mcp_demo" to "cymbal_coffee" to match the project branding.

## Acceptance Criteria

### 1. Idempotent Installation
- [x] `manage.py install uv` - Only installs if `uv` command not in PATH
- [x] `manage.py install sqlcl` - Only installs if `sql` command not in PATH
- [x] `manage.py install gemini-cli` - Only installs if `gemini` command not in PATH
- [x] `manage.py install mcp-toolbox` - Only installs if `toolbox` command not in PATH
- [x] `Makefile install-uv` - Idempotent UV installation
- [x] `Makefile install-sqlcl` - Idempotent SQLcl installation
- [x] All installations display informative messages when already present

### 2. Cross-Configuration
- [x] When `gemini-cli` is installed, auto-configure SQLcl MCP server if SQLcl exists
- [x] When `sqlcl` is installed, auto-configure in gemini-cli if gemini-cli exists
- [x] MCP configuration is additive (never overwrites existing MCP servers)
- [x] Saved SQLcl connection is created with password only if needed

### 3. Connection Naming
- [x] Default SQLcl connection renamed from "mcp_demo" to "cymbal_coffee"
- [x] Update `manage.py` connection name references
- [x] Update `docs/guides/gemini-mcp-integration.md` examples
- [x] Ensure backward compatibility (detect and migrate existing "mcp_demo" connections)

### 4. Detection & Validation
- [x] Each installer validates installation after completion
- [x] Clear success/skip messages for user feedback
- [x] `--force` flag allows re-installation when needed (changed from --if-missing)
- [x] Idempotent by default (no flag needed)

## Technical Design

### Current State Analysis

#### Installation Entry Points

**manage.py commands:**
- `install uv` (lines 744-831)
- `install sqlcl` (lines 834-939)
- `install gemini-cli` (lines 941-1070)
- `install mcp-toolbox` (lines 1073-1164)
- `install all` (lines 618-686)

**Makefile targets:**
- `install-uv` (lines 41-45)
- `install-sqlcl` (lines 35-39)

**Current Detection Logic:**
- UV: `shutil.which("uv")` at line 769 (only checks if `--if-missing` flag used)
- SQLcl: Java check at line 860, but no SQLcl existence check
- Gemini CLI: `shutil.which("gemini")` at line 962 (only if `--if-missing` flag used)
- MCP Toolbox: `shutil.which("toolbox")` at line 1096 (only if `--if-missing` flag used)

**Issues:**
1. Detection only happens when `--if-missing` flag is used
2. No detection by default - will attempt re-installation
3. Cross-configuration happens but doesn't check if already configured
4. Connection name hardcoded as "mcp_demo" in multiple places

### Data Model Changes

**None required** - All changes are to installation scripts and documentation.

### API Design

#### New Utility Functions (in manage.py)

```python
def is_tool_installed(tool_name: str) -> bool:
    """Check if a tool is installed and available in PATH.

    Args:
        tool_name: Name of the executable to check (e.g., 'uv', 'sql', 'gemini')

    Returns:
        bool: True if tool is in PATH and executable
    """
    return shutil.which(tool_name) is not None


def is_mcp_server_configured(server_name: str) -> bool:
    """Check if an MCP server is already configured in Gemini settings.

    Args:
        server_name: Name of the MCP server (e.g., 'sqlcl', 'sequential-thinking')

    Returns:
        bool: True if server is already configured
    """
    gemini_settings_path = Path.home() / ".gemini" / "settings.json"
    if not gemini_settings_path.exists():
        return False

    try:
        with open(gemini_settings_path) as f:
            settings = json.load(f)
        return server_name in settings.get("mcpServers", {})
    except Exception:
        return False


def is_sqlcl_connection_saved(connection_name: str = "cymbal_coffee") -> bool:
    """Check if a SQLcl saved connection exists.

    Args:
        connection_name: Name of the saved connection

    Returns:
        bool: True if connection is saved
    """
    # SQLcl saved connections are stored in ~/.sqlcl/connections.json
    # or can be tested with: sql -L (list connections)
    if not shutil.which("sql"):
        return False

    try:
        result = subprocess.run(
            ["sql", "-L"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return connection_name in result.stdout
    except Exception:
        return False


def migrate_sqlcl_connection(old_name: str = "mcp_demo", new_name: str = "cymbal_coffee") -> bool:
    """Migrate old SQLcl connection name to new name.

    Args:
        old_name: Old connection name to rename
        new_name: New connection name

    Returns:
        bool: True if migration successful or not needed
    """
    # Implementation: Delete old connection and recreate with new name
    # Returns True if old doesn't exist (nothing to migrate)
    # Returns True if successfully migrated
    # Returns False if migration failed
    pass
```

#### Modified Functions

**install_uv()** (lines 744-831):
```python
@install.command(name="uv")
@click.option("--version", help="Specific version to install (default: latest)")
@click.option("--if-missing", is_flag=True, help="Only install if UV not already present")
@click.option("--force", is_flag=True, help="Force reinstall even if already installed")
def install_uv(version: str | None, if_missing: bool, force: bool) -> None:
    """Install Astral's UV package manager."""

    # ALWAYS check if installed (not just when --if-missing)
    uv_path = shutil.which("uv")
    if uv_path and not force:
        returncode, stdout, _ = run_command(["uv", "--version"], check=False)
        if returncode == 0:
            console.print(f"[green]✓ UV already installed: {stdout.strip()}[/green]")
            console.print(f"[dim]  Location: {uv_path}[/dim]")
            console.print("[dim]  Use --force to reinstall[/dim]")
            return

    # Proceed with installation...
```

**install_sqlcl()** (lines 834-939):
```python
@install.command(name="sqlcl")
@click.option("--dir", "install_dir", type=click.Path(), help="Installation directory (default: ~/.local/bin)")
@click.option("--force", is_flag=True, help="Reinstall even if already installed")
@click.option("--connection-name", default="cymbal_coffee", help="Name for saved SQLcl connection")
def install_sqlcl(install_dir: str | None, force: bool, connection_name: str) -> None:
    """Install Oracle SQLcl command-line tool."""

    # Check if already installed
    sqlcl_path = shutil.which("sql")
    if sqlcl_path and not force:
        returncode, stdout, _ = run_command(["sql", "-V"], check=False)
        if returncode == 0:
            console.print(f"[green]✓ SQLcl already installed: {stdout.strip()}[/green]")
            console.print(f"[dim]  Location: {sqlcl_path}[/dim]")
            console.print("[dim]  Use --force to reinstall[/dim]")

            # Still check for Gemini MCP configuration
            if is_tool_installed("gemini") and not is_mcp_server_configured("sqlcl"):
                console.print("\n[yellow]🔐 Configuring SQLcl for Gemini MCP...[/yellow]")
                # Configure MCP integration...

            return

    # Proceed with installation...
    # After installation, use connection_name instead of "mcp_demo"
```

**install_gemini_cli()** (lines 941-1070):
```python
@install.command(name="gemini-cli")
@click.option("--if-missing", is_flag=True, help="Only install if not already present")
@click.option("--force", is_flag=True, help="Force reinstall even if already installed")
@click.option("--configure-mcp", is_flag=True, default=True, help="Configure MCP extensions")
def install_gemini_cli(if_missing: bool, force: bool, configure_mcp: bool) -> None:
    """Install Google Gemini CLI."""

    # ALWAYS check if installed
    gemini_path = shutil.which("gemini")
    if gemini_path and not force:
        returncode, stdout, _ = run_command(["gemini", "--version"], check=False)
        if returncode == 0:
            console.print(f"[green]✓ Gemini CLI already installed: {stdout.strip()}[/green]")
            console.print(f"[dim]  Location: {gemini_path}[/dim]")
            console.print("[dim]  Use --force to reinstall[/dim]")

            # Still check for MCP configuration
            if configure_mcp:
                console.print("\n[yellow]🔧 Checking MCP configuration...[/yellow]")
                # Configure missing MCP servers only
                configure_missing_mcp_extensions()

            return

    # Proceed with installation...
```

**configure_gemini_mcp_sqlcl()** (lines 316-366):
```python
def configure_gemini_mcp_sqlcl() -> bool:
    """Configure SQLcl as a Gemini MCP server.

    Returns:
        bool: True if configuration was successful or already exists
    """
    # Check if already configured
    if is_mcp_server_configured("sqlcl"):
        console.print("[green]✓ SQLcl MCP server already configured[/green]")
        return True

    # Proceed with configuration...
    # (existing implementation)
```

**configure_sqlcl_connection_with_password()** (lines 243-313):
```python
def configure_sqlcl_connection_with_password(connection_name: str = "cymbal_coffee") -> tuple[bool, str]:
    """Configure SQLcl saved connection with password from .env.

    Args:
        connection_name: Name for the saved connection (default: cymbal_coffee)

    Returns:
        tuple[bool, str]: Success status and message
    """
    # Check if connection already exists
    if is_sqlcl_connection_saved(connection_name):
        return True, f"Connection '{connection_name}' already configured"

    # Check for old connection name and migrate
    if is_sqlcl_connection_saved("mcp_demo"):
        console.print("[yellow]🔄 Migrating old connection 'mcp_demo' to '{connection_name}'...[/yellow]")
        if migrate_sqlcl_connection("mcp_demo", connection_name):
            return True, f"Migrated connection to '{connection_name}'"

    # Proceed with new connection creation...
    # (existing implementation with connection_name parameter)
```

**configure_gemini_mcp_extensions()** (lines 369-452):
```python
def configure_gemini_mcp_extensions(interactive: bool = True) -> dict[str, bool]:
    """Configure popular Gemini MCP extensions.

    CHANGED: Only configure extensions that aren't already configured.
    Skip already configured extensions silently.
    """
    # ...existing code...

    # Configure each extension
    for key, ext in extensions.items():
        # Check if already configured (SKIP if exists)
        if is_mcp_server_configured(key):
            console.print(f"[dim]ℹ {ext['name']} already configured (skipping)[/dim]")
            results[key] = True  # Already configured = success
            continue

        # Interactive prompt for NEW extensions only
        should_install = True
        if interactive:
            console.print()
            console.print(f"[bold cyan]{ext['name']}[/bold cyan]")
            console.print(f"[dim]{ext['description']}[/dim]")
            should_install = Confirm.ask(f"Configure {ext['name']}?", default=True)

        if should_install:
            settings["mcpServers"][key] = ext["config"]
            results[key] = True
        else:
            results[key] = False

    # ...rest of existing code...
```

### Integration Points

#### Makefile Integration

Update Makefile targets to be idempotent by default:

```makefile
.PHONY: install-uv
install-uv: ## Install latest version of uv (idempotent)
	@if command -v uv >/dev/null 2>&1; then \
		echo "${OK} UV already installed: $$(uv --version)"; \
	else \
		echo "${INFO} Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; \
		echo "${OK} UV installed successfully"; \
	fi

.PHONY: install-sqlcl
install-sqlcl: ## Install Oracle SQLcl to ~/.local/bin (idempotent)
	@if command -v sql >/dev/null 2>&1; then \
		echo "${OK} SQLcl already installed: $$(sql -V 2>&1 | head -n1)"; \
	else \
		echo "${INFO} Installing Oracle SQLcl..."; \
		uv run tools/install_sqlcl.py; \
		echo "${OK} SQLcl installation complete!"; \
	fi
```

#### Cross-Configuration Flow

**Scenario 1: Install SQLcl when Gemini CLI exists**
```
1. Check if `sql` in PATH → Not found
2. Install SQLcl
3. Validate installation
4. Check if `gemini` in PATH → Found
5. Check if sqlcl MCP server configured → Not configured
6. Configure saved connection "cymbal_coffee"
7. Add sqlcl to ~/.gemini/settings.json
8. Success message with MCP configured
```

**Scenario 2: Install Gemini CLI when SQLcl exists**
```
1. Check if `gemini` in PATH → Not found
2. Install Gemini CLI via npm
3. Validate installation
4. Check if `sql` in PATH → Found
5. Prompt: "Configure SQLcl MCP server? [Y/n]"
6. If Yes:
   - Check if connection "cymbal_coffee" exists → Create if needed
   - Add sqlcl to ~/.gemini/settings.json (if not already there)
7. Prompt for other MCP extensions (sequential-thinking, context7)
8. Success message with all configured MCPs
```

**Scenario 3: Re-run install sqlcl (already installed)**
```
1. Check if `sql` in PATH → Found
2. Get version: sql -V
3. Display: "✓ SQLcl already installed: SQLcl: Release 24.3.0"
4. Display: "Use --force to reinstall"
5. Check if Gemini MCP configured → Yes
6. Display: "✓ Gemini MCP integration already configured"
7. Exit (no changes made)
```

**Scenario 4: Re-run install gemini-cli (already installed)**
```
1. Check if `gemini` in PATH → Found
2. Get version: gemini --version
3. Display: "✓ Gemini CLI already installed: 1.2.3"
4. Display: "Use --force to reinstall"
5. Check MCP extensions:
   - sqlcl: configured → Skip
   - sequential-thinking: not configured → Prompt to configure
   - context7: configured → Skip
6. Configure only missing MCP extensions
7. Exit
```

## Dependencies

- Must not break existing installations
- Must work with current .env structure
- Must preserve existing MCP configurations
- Must work with both Docker and Podman (already abstracted)

## Risks & Mitigations

### Risk 1: Breaking Existing Workflows
**Description**: Users with existing "mcp_demo" connections will break.

**Mitigation**:
- Implement migration function to rename existing connection
- Check for "mcp_demo" before creating "cymbal_coffee"
- Automatically migrate if old connection exists
- Log migration action for transparency

### Risk 2: MCP Configuration Corruption
**Description**: JSON manipulation could corrupt ~/.gemini/settings.json.

**Mitigation**:
- Always validate JSON before writing
- Create backup of settings.json before modification
- Use try/except blocks with rollback on error
- Validate JSON syntax after writing

### Risk 3: False Positive Detection
**Description**: Tool in PATH but broken/non-functional.

**Mitigation**:
- Don't just check `which` - also run `tool --version`
- Validate return code (must be 0)
- For SQLcl, also check if sql -V returns valid output
- Provide `--force` flag to override detection

### Risk 4: Cross-Configuration Race Conditions
**Description**: Installing both tools simultaneously could cause conflicts.

**Mitigation**:
- Use file locking for ~/.gemini/settings.json writes
- Read-modify-write in single atomic operation
- Detect if file changed between read and write
- Retry on concurrent modification

## Testing Strategy

### Unit Tests
- `test_is_tool_installed()` - Mock shutil.which
- `test_is_mcp_server_configured()` - Mock settings.json content
- `test_is_sqlcl_connection_saved()` - Mock `sql -L` output
- `test_migrate_sqlcl_connection()` - Integration test with temp SQLcl config

### Integration Tests
- Install UV twice → Second time skips with message
- Install SQLcl twice → Second time skips, checks MCP config
- Install Gemini CLI twice → Second time skips, checks missing MCPs
- Install SQLcl then Gemini → Cross-configures correctly
- Install Gemini then SQLcl → Cross-configures correctly

### Manual Test Scenarios
1. **Fresh Install**: Run all installers on clean system
2. **Re-run All**: Run all installers again → All skip gracefully
3. **Partial Install**: Install only UV → Run install all → Skips UV, installs rest
4. **Migration Test**: Create "mcp_demo" connection → Install SQLcl → Verify migration
5. **MCP Only**: Install Gemini with existing SQLcl → Only configures MCP
6. **Force Reinstall**: Use --force flag → Actually reinstalls

## Documentation Updates

### Files to Update

**1. docs/guides/gemini-mcp-integration.md**
- Line 108-109: Change `mcp_demo` to `cymbal_coffee`
- Line 361: Change `mcp_demo` to `cymbal_coffee`
- Add section on idempotency behavior
- Add section on connection name migration

**2. manage.py docstrings**
- Update `install uv` docstring to mention idempotency
- Update `install sqlcl` docstring to mention idempotency and connection name
- Update `install gemini-cli` docstring to mention MCP re-configuration behavior
- Update `install all` docstring to mention idempotent behavior

**3. New documentation section**
- Create "Installation Best Practices" section in README or setup guide
- Document `--force` and `--if-missing` flags (note: --if-missing becomes default behavior)
- Document connection name change and migration

## Estimated Effort

**Complexity**: Medium

**Time Estimate**: 4-6 hours
- Analysis & Planning: 1 hour (DONE)
- Implementation: 2-3 hours
- Testing: 1-2 hours
- Documentation: 1 hour

**Files Modified**: 3
- `manage.py` (main implementation)
- `Makefile` (idempotent targets)
- `docs/guides/gemini-mcp-integration.md` (connection name updates)

**Lines of Code**: ~200-300 LOC (modifications + new utility functions)

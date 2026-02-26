# Detailed Tasks for Idempotent Installation Commands

## Task 1: Add Utility Functions

### 1.1 Add `is_tool_installed()` Helper

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Location**: After `run_command()` function (around line 242)

**Implementation**:
```python
def is_tool_installed(tool_name: str, version_flag: str = "--version") -> tuple[bool, str]:
    """Check if a tool is installed and available in PATH.

    Args:
        tool_name: Name of the executable to check (e.g., 'uv', 'sql', 'gemini')
        version_flag: Flag to get version (default: '--version')

    Returns:
        tuple[bool, str]: (is_installed, version_string)
    """
    if not shutil.which(tool_name):
        return False, ""

    try:
        returncode, stdout, _ = run_command([tool_name, version_flag], check=False)
        if returncode == 0:
            return True, stdout.strip()
    except Exception:
        pass

    return False, ""
```

**Test Cases**:
- UV installed: `is_tool_installed("uv")` → `(True, "uv 0.5.15")`
- SQLcl installed: `is_tool_installed("sql", "-V")` → `(True, "SQLcl: Release 24.3.0")`
- Not installed: `is_tool_installed("nonexistent")` → `(False, "")`

### 1.2 Add `is_mcp_server_configured()` Helper

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Location**: After `is_tool_installed()` function

**Implementation**:
```python
def is_mcp_server_configured(server_name: str) -> bool:
    """Check if an MCP server is already configured in Gemini settings.

    Args:
        server_name: Name of the MCP server (e.g., 'sqlcl', 'sequential-thinking')

    Returns:
        bool: True if server is already configured
    """
    import json

    gemini_settings_path = Path.home() / ".gemini" / "settings.json"
    if not gemini_settings_path.exists():
        return False

    try:
        with open(gemini_settings_path) as f:
            settings = json.load(f)
        mcp_servers = settings.get("mcpServers", {})
        # Check if server exists and is not None/null
        return server_name in mcp_servers and mcp_servers[server_name] is not None
    except Exception:
        return False
```

**Test Cases**:
- Configured server: `is_mcp_server_configured("sqlcl")` → `True`
- Not configured: `is_mcp_server_configured("nonexistent")` → `False`
- Disabled server (null): `is_mcp_server_configured("disabled")` → `False`

### 1.3 Add `is_sqlcl_connection_saved()` Helper

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Location**: After `is_mcp_server_configured()` function

**Implementation**:
```python
def is_sqlcl_connection_saved(connection_name: str = "cymbal_coffee") -> bool:
    """Check if a SQLcl saved connection exists.

    Args:
        connection_name: Name of the saved connection

    Returns:
        bool: True if connection is saved
    """
    if not shutil.which("sql"):
        return False

    try:
        # Use sql -L to list saved connections
        result = subprocess.run(
            ["sql", "-L"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        # Check if connection_name appears in the output
        return connection_name in result.stdout
    except Exception:
        return False
```

**Test Cases**:
- Connection exists: `is_sqlcl_connection_saved("cymbal_coffee")` → `True`
- Connection missing: `is_sqlcl_connection_saved("nonexistent")` → `False`
- SQLcl not installed: `is_sqlcl_connection_saved("any")` → `False`

### 1.4 Add `migrate_sqlcl_connection()` Helper

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Location**: After `is_sqlcl_connection_saved()` function

**Implementation**:
```python
def migrate_sqlcl_connection(
    old_name: str = "mcp_demo",
    new_name: str = "cymbal_coffee"
) -> tuple[bool, str]:
    """Migrate old SQLcl connection name to new name.

    Args:
        old_name: Old connection name to rename
        new_name: New connection name

    Returns:
        tuple[bool, str]: (success, message)
    """
    from dotenv import dotenv_values

    # Check if old connection exists
    if not is_sqlcl_connection_saved(old_name):
        return True, f"No '{old_name}' connection to migrate"

    # Check if new connection already exists
    if is_sqlcl_connection_saved(new_name):
        return True, f"Connection '{new_name}' already exists"

    # Load credentials from .env
    env_path = Path(".env")
    if not env_path.exists():
        return False, ".env file not found"

    env_vars = dotenv_values(env_path)
    user = env_vars.get("DATABASE_USER")
    password = env_vars.get("DATABASE_PASSWORD")
    host = env_vars.get("DATABASE_HOST")
    port = env_vars.get("DATABASE_PORT", "1521")
    service_name = env_vars.get("DATABASE_SERVICE_NAME")

    if not all([user, password, host, service_name]):
        return False, "Missing database credentials in .env"

    # Create new connection with new name
    conn_string = f"{user}/{password}@//{host}:{port}/{service_name}"
    conn_cmd = f"conn -save {new_name} -savepwd {conn_string}\nexit"

    try:
        result = subprocess.run(
            ["sql", "/nolog"],
            check=False,
            input=conn_cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            # TODO: Delete old connection (SQLcl doesn't have a delete command)
            # For now, just create the new one and leave the old one
            return True, f"Created connection '{new_name}' (old '{old_name}' still exists)"
        return False, "Failed to create new connection"

    except subprocess.TimeoutExpired:
        return False, "SQLcl command timed out"
    except Exception as e:
        return False, f"Error migrating connection: {e}"
```

**Test Cases**:
- Old exists, new doesn't: Creates new connection
- Old doesn't exist: Returns success (nothing to migrate)
- New already exists: Returns success (already migrated)
- Missing .env: Returns failure

---

## Task 2: Make UV Installation Idempotent

### 2.1 Modify `install_uv()` Function

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Lines**: 744-831

**Changes**:

**Before**:
```python
@install.command(name="uv")
@click.option("--version", help="Specific version to install (default: latest)")
@click.option("--if-missing", is_flag=True, help="Only install if UV not already present")
def install_uv(version: str | None, if_missing: bool) -> None:
    """Install Astral's UV package manager."""
    console.print("[yellow]📦 Installing UV package manager...[/yellow]")
    console.print()

    # Check if already installed
    uv_path = shutil.which("uv")
    if uv_path and if_missing:  # <-- Only checks if flag is set
        returncode, stdout, _ = run_command(["uv", "--version"], check=False)
        if returncode == 0:
            console.print(f"[green]✓ UV already installed: {stdout.strip()}[/green]")
            console.print(f"[dim]  Location: {uv_path}[/dim]")
            return
```

**After**:
```python
@install.command(name="uv")
@click.option("--version", help="Specific version to install (default: latest)")
@click.option("--force", is_flag=True, help="Force reinstall even if already installed")
def install_uv(version: str | None, force: bool) -> None:
    """Install Astral's UV package manager.

    Idempotent: Safe to run multiple times. Skips installation if UV is already
    installed unless --force flag is used.
    """
    console.print("[yellow]📦 Checking UV installation...[/yellow]")
    console.print()

    # ALWAYS check if already installed (not just when flag is set)
    is_installed, version_str = is_tool_installed("uv")
    if is_installed and not force:
        console.print(f"[green]✓ UV already installed: {version_str}[/green]")
        uv_path = shutil.which("uv")
        console.print(f"[dim]  Location: {uv_path}[/dim]")
        console.print("[dim]  Use --force to reinstall[/dim]")
        return

    # Proceed with installation
    if is_installed and force:
        console.print(f"[yellow]⚠ Reinstalling UV (--force flag used)[/yellow]")
    else:
        console.print("[yellow]📦 Installing UV package manager...[/yellow]")

    console.print()

    # ... rest of installation logic unchanged ...
```

**Note**: Remove `--if-missing` flag (idempotency is now default behavior)

### 2.2 Update Makefile `install-uv` Target

**File**: `/home/cody/code/g/oracledb-vertexai-demo/Makefile`
**Lines**: 41-45

**Before**:
```makefile
.PHONY: install-uv
install-uv:                                         ## Install latest version of uv
	@echo "${INFO} Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
	@echo "${OK} UV installed successfully"
```

**After**:
```makefile
.PHONY: install-uv
install-uv:                                         ## Install latest version of uv (idempotent)
	@if command -v uv >/dev/null 2>&1; then \
		echo "${OK} UV already installed: $$(uv --version)"; \
	else \
		echo "${INFO} Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; \
		echo "${OK} UV installed successfully"; \
	fi
```

### 2.3 Test UV Re-installation Behavior

**Test Script**:
```bash
# Test 1: Fresh install
python manage.py install uv
# Expected: Installs UV

# Test 2: Re-run install (should skip)
python manage.py install uv
# Expected: "✓ UV already installed: uv 0.5.15"
#           "Use --force to reinstall"

# Test 3: Force reinstall
python manage.py install uv --force
# Expected: "⚠ Reinstalling UV (--force flag used)"
#           Downloads and installs

# Test 4: Makefile target (already installed)
make install-uv
# Expected: "✓ UV already installed: uv 0.5.15"

# Test 5: Makefile target (not installed)
# (Remove uv from PATH temporarily)
make install-uv
# Expected: Installs UV
```

---

## Task 3: Make SQLcl Installation Idempotent

### 3.1 Modify `install_sqlcl()` Function

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Lines**: 834-939

**Changes**:

**Add new parameter**:
```python
@install.command(name="sqlcl")
@click.option("--dir", "install_dir", type=click.Path(), help="Installation directory (default: ~/.local/bin)")
@click.option("--force", is_flag=True, help="Reinstall even if already installed")
@click.option("--connection-name", default="cymbal_coffee", help="Name for saved SQLcl connection")
def install_sqlcl(install_dir: str | None, force: bool, connection_name: str) -> None:
    """Install Oracle SQLcl command-line tool.

    Idempotent: Safe to run multiple times. Skips installation if SQLcl is already
    installed unless --force flag is used.

    Optional tool for advanced Oracle database operations.
    Requires Java 11 or higher to be installed.
    """
    from tools.oracle_deploy import cli as oracle_cli

    console.print("[yellow]📦 Checking SQLcl installation...[/yellow]")
    console.print()

    # Check for Java before proceeding
    java_path = shutil.which("java")
    if not java_path:
        # ... existing Java error message ...
        raise click.Abort()

    # Check if already installed
    is_installed, version_str = is_tool_installed("sql", "-V")
    if is_installed and not force:
        console.print(f"[green]✓ SQLcl already installed: {version_str.split('\\n')[0]}[/green]")
        sqlcl_path = shutil.which("sql")
        console.print(f"[dim]  Location: {sqlcl_path}[/dim]")
        console.print("[dim]  Use --force to reinstall[/dim]")

        # Still check for Gemini MCP configuration
        gemini_path = shutil.which("gemini")
        if gemini_path:
            console.print()
            console.print("[yellow]🔐 Checking Gemini MCP integration...[/yellow]")

            # Check if already configured
            if is_mcp_server_configured("sqlcl"):
                console.print("[green]✓ SQLcl MCP server already configured[/green]")
            else:
                console.print("[yellow]🔐 Configuring SQLcl for Gemini MCP...[/yellow]")

                # Step 1: Configure saved connection with password
                success, message = configure_sqlcl_connection_with_password(connection_name)
                if success:
                    console.print(f"[green]✓ {message}[/green]")
                else:
                    console.print(f"[yellow]⚠ Password configuration: {message}[/yellow]")

                # Step 2: Configure Gemini MCP server
                if configure_gemini_mcp_sqlcl():
                    console.print("[green]✓ Configured SQLcl as Gemini MCP server[/green]")

        return

    # If force flag, show warning
    if is_installed and force:
        console.print(f"[yellow]⚠ Reinstalling SQLcl (--force flag used)[/yellow]")
        console.print()

    console.print("[yellow]📦 Installing Oracle SQLcl...[/yellow]")
    console.print()

    # Check Java version (existing code)
    returncode, stdout, _ = run_command(["java", "-version"], check=False)
    if returncode == 0:
        console.print("[green]✓ Java found[/green]")
        console.print()

    # Delegate to existing implementation
    args = ["sqlcl", "install"]
    if install_dir:
        args.extend(["--dir", install_dir])
    if force:
        args.append("--force")

    ctx = click.get_current_context()
    try:
        oracle_cli.main(args, standalone_mode=False)
    except SystemExit:
        pass

    # Post-installation instructions (existing code)
    console.print()
    console.print("[bold]Test SQLcl:[/bold]")
    console.print("  [cyan]sql -V[/cyan]")
    console.print()

    # Configure Gemini MCP integration (using connection_name parameter)
    gemini_path = shutil.which("gemini")
    if gemini_path:
        console.print()
        console.print("[yellow]🔐 Configuring SQLcl MCP integration...[/yellow]")

        # Step 1: Configure saved connection with password
        success, message = configure_sqlcl_connection_with_password(connection_name)
        if success:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[yellow]⚠ Password configuration: {message}[/yellow]")

        # Step 2: Configure Gemini MCP server
        if configure_gemini_mcp_sqlcl():
            console.print("[green]✓ Configured SQLcl as Gemini MCP server[/green]")
```

### 3.2 Update `configure_sqlcl_connection_with_password()` Function

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Lines**: 243-313

**Changes**:

```python
def configure_sqlcl_connection_with_password(connection_name: str = "cymbal_coffee") -> tuple[bool, str]:
    """Configure SQLcl saved connection with password from .env.

    Args:
        connection_name: Name for the saved connection (default: cymbal_coffee)

    Returns:
        tuple[bool, str]: Success status and message

    SQLcl MCP requires a saved connection with password using the -savepwd flag.
    This function creates a saved connection using credentials from .env.

    Command format:
        conn -save <name> -savepwd username/password@//host:port/service
    """
    from dotenv import dotenv_values

    # Check if connection already exists
    if is_sqlcl_connection_saved(connection_name):
        return True, f"Connection '{connection_name}' already configured"

    # Check for old connection name and migrate
    if connection_name == "cymbal_coffee" and is_sqlcl_connection_saved("mcp_demo"):
        console.print("[yellow]🔄 Migrating old connection 'mcp_demo' to 'cymbal_coffee'...[/yellow]")
        success, message = migrate_sqlcl_connection("mcp_demo", "cymbal_coffee")
        if success:
            return True, message
        console.print(f"[yellow]⚠ Migration warning: {message}[/yellow]")
        # Continue to create new connection even if migration failed

    # Load .env values
    env_path = Path(".env")
    if not env_path.exists():
        return False, ".env file not found - run 'python manage.py init' first"

    env_vars = dotenv_values(env_path)

    # ... rest of existing implementation ...
    # (Use connection_name parameter instead of hardcoded "mcp_demo")

    # Build connection string (Oracle format with //)
    conn_string = f"{user}/{password}@//{host}:{port}/{service_name}"

    # Use echo to pipe the connection command
    conn_cmd = f"conn -save {connection_name} -savepwd {conn_string}\nexit"  # <-- Use parameter

    try:
        result = subprocess.run(
            ["sql", "/nolog"],
            check=False,
            input=conn_cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Check if successful
        if result.returncode == 0:
            return True, f"Saved connection '{connection_name}' configured for {user}@//{host}:{port}/{service_name}"
        error_msg = result.stderr or result.stdout
        return False, f"Failed to save connection: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "SQLcl command timed out"
    except Exception as e:
        return False, f"Error running SQLcl: {e}"
```

### 3.3 Update Makefile `install-sqlcl` Target

**File**: `/home/cody/code/g/oracledb-vertexai-demo/Makefile`
**Lines**: 35-39

**Before**:
```makefile
.PHONY: install-sqlcl
install-sqlcl: ## Install Oracle SQLcl to ~/.local/bin
	@echo "${INFO} Installing Oracle SQLcl..."
	@uv run tools/install_sqlcl.py
	@echo "${OK} SQLcl installation complete!"
```

**After**:
```makefile
.PHONY: install-sqlcl
install-sqlcl: ## Install Oracle SQLcl to ~/.local/bin (idempotent)
	@if command -v sql >/dev/null 2>&1; then \
		echo "${OK} SQLcl already installed: $$(sql -V 2>&1 | head -n1)"; \
	else \
		echo "${INFO} Installing Oracle SQLcl..."; \
		uv run python manage.py install sqlcl; \
		echo "${OK} SQLcl installation complete!"; \
	fi
```

### 3.4 Test SQLcl Re-installation Behavior

**Test Script**:
```bash
# Test 1: Fresh install with new connection name
python manage.py install sqlcl
# Expected: Installs SQLcl, creates "cymbal_coffee" connection

# Test 2: Re-run install (should skip)
python manage.py install sqlcl
# Expected: "✓ SQLcl already installed"
#           "✓ SQLcl MCP server already configured"

# Test 3: Custom connection name
python manage.py install sqlcl --connection-name my_db
# Expected: Skips install, checks/creates "my_db" connection

# Test 4: Migration from old connection name
# (Manually create "mcp_demo" connection first)
sql /nolog <<EOF
conn -save mcp_demo -savepwd app/password@//localhost:1521/freepdb1
exit
EOF

python manage.py install sqlcl
# Expected: "🔄 Migrating old connection 'mcp_demo' to 'cymbal_coffee'..."
#           "✓ Created connection 'cymbal_coffee'"

# Test 5: Cross-configuration (Gemini already installed)
# (Install Gemini first)
python manage.py install gemini-cli
python manage.py install sqlcl
# Expected: Skips install, configures MCP if not already configured
```

---

## Task 4: Make Gemini CLI Installation Idempotent

### 4.1 Modify `install_gemini_cli()` Function

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Lines**: 941-1070

**Changes**:

```python
@install.command(name="gemini-cli")
@click.option("--force", is_flag=True, help="Force reinstall even if already installed")
@click.option("--configure-mcp", is_flag=True, default=True, help="Configure MCP extensions")
def install_gemini_cli(force: bool, configure_mcp: bool) -> None:
    """Install Google Gemini CLI.

    Idempotent: Safe to run multiple times. Skips installation if Gemini CLI is
    already installed unless --force flag is used.

    AI-powered terminal assistant with access to Gemini 2.5 Pro.
    Requires Node.js 18 or higher.

    Features:
    - Free tier: 60 requests/min, 1000 requests/day
    - 1M token context window
    - Built-in tools: Google Search, file ops, shell commands
    """
    console.print("[yellow]📦 Checking Gemini CLI installation...[/yellow]")
    console.print()

    # Check if already installed
    is_installed, version_str = is_tool_installed("gemini")
    if is_installed and not force:
        console.print(f"[green]✓ Gemini CLI already installed: {version_str}[/green]")
        gemini_path = shutil.which("gemini")
        console.print(f"[dim]  Location: {gemini_path}[/dim]")
        console.print("[dim]  Use --force to reinstall[/dim]")

        # Still check for MCP configuration
        if configure_mcp:
            console.print()
            console.print("[yellow]🔧 Checking MCP configuration...[/yellow]")
            configure_missing_mcp_extensions()

        return

    # Check for Node.js (existing code)
    node_path = shutil.which("node")
    if not node_path:
        # ... existing Node.js error message ...
        raise click.Abort()

    # If force flag, show warning
    if is_installed and force:
        console.print(f"[yellow]⚠ Reinstalling Gemini CLI (--force flag used)[/yellow]")
        console.print()

    # ... rest of installation logic ...
```

### 4.2 Add `configure_missing_mcp_extensions()` Helper Function

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Location**: Before `install_gemini_cli()` function (around line 940)

**Implementation**:
```python
def configure_missing_mcp_extensions() -> None:
    """Configure MCP extensions that are not already configured.

    Checks for:
    - SQLcl (if installed and not configured)
    - Sequential Thinking (if not configured)
    - Context7 (if not configured)

    Only prompts for missing extensions.
    """
    import json

    gemini_settings_path = Path.home() / ".gemini" / "settings.json"

    # Check SQLcl
    sqlcl_path = shutil.which("sql")
    if sqlcl_path and not is_mcp_server_configured("sqlcl"):
        console.print()
        console.print("[bold cyan]SQLcl (Oracle Database)[/bold cyan]")
        console.print("[dim]Oracle database operations and SQL execution[/dim]")
        if Confirm.ask("Configure SQLcl MCP server?", default=True):
            # Step 1: Configure saved connection with password
            success, message = configure_sqlcl_connection_with_password()
            if success:
                console.print(f"[green]✓[/green] {message}")
            else:
                console.print(f"[yellow]⚠[/yellow] Password config: {message}")

            # Step 2: Configure Gemini MCP server
            if configure_gemini_mcp_sqlcl():
                console.print("[green]✓[/green] SQLcl MCP server configured")
    elif sqlcl_path:
        console.print("[dim]ℹ SQLcl MCP server already configured[/dim]")

    # Configure other MCP extensions (only missing ones)
    results = configure_gemini_mcp_extensions(interactive=True)

    # Show summary
    console.print()
    console.print("[bold]MCP Configuration Summary:[/bold]")
    if sqlcl_path and is_mcp_server_configured("sqlcl"):
        console.print("  [green]✓[/green] sqlcl (Oracle Database)")
    for key, success in results.items():
        if success:
            console.print(f"  [green]✓[/green] {key}")
        else:
            console.print(f"  [dim]⊘ {key} (skipped)[/dim]")
```

### 4.3 Update `configure_gemini_mcp_extensions()` Function

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Lines**: 369-452

**Changes**:

```python
def configure_gemini_mcp_extensions(interactive: bool = True) -> dict[str, bool]:
    """Configure popular Gemini MCP extensions.

    Args:
        interactive: If True, prompt user for each extension

    Returns:
        dict: Status of each extension configuration {extension_name: success}

    Configures:
    - sequential-thinking: Advanced reasoning capabilities
    - context7: Documentation and code context from popular libraries

    IMPORTANT: Only configures extensions that aren't already configured.
    """
    import json

    gemini_settings_path = Path.home() / ".gemini" / "settings.json"
    results = {}

    # Check if Gemini settings directory exists
    if not gemini_settings_path.parent.exists():
        try:
            gemini_settings_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            return {"error": False}

    # Read existing settings or create new
    settings: dict[str, Any] = {}
    if gemini_settings_path.exists():
        try:
            with open(gemini_settings_path) as f:
                settings = json.load(f)
        except Exception:
            return {"error": False}

    # Ensure mcpServers key exists
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    # Define extensions
    extensions = {
        "sequential-thinking": {
            "name": "Sequential Thinking",
            "description": "Advanced reasoning with step-by-step problem solving",
            "config": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            },
        },
        "context7": {
            "name": "Context7",
            "description": "Documentation lookup for popular libraries and frameworks",
            "config": {"command": "npx", "args": ["-y", "@upstash/context7-mcp"]},
        },
    }

    # Configure each extension
    for key, ext in extensions.items():
        # Check if already configured (SKIP if exists)
        if is_mcp_server_configured(key):
            if interactive:
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

    # Write back to file
    try:
        with open(gemini_settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        return results
    except Exception:
        return dict.fromkeys(extensions.keys(), False)
```

### 4.4 Test Gemini CLI Re-installation Behavior

**Test Script**:
```bash
# Test 1: Fresh install
python manage.py install gemini-cli
# Expected: Installs Gemini CLI, prompts for all MCP extensions

# Test 2: Re-run install (should skip)
python manage.py install gemini-cli
# Expected: "✓ Gemini CLI already installed"
#           Checks MCP configuration, shows "already configured" for existing

# Test 3: Install with SQLcl already present
python manage.py install sqlcl
python manage.py install gemini-cli
# Expected: Installs Gemini, prompts to configure SQLcl MCP

# Test 4: Re-run after partial MCP config
# (Manually remove context7 from settings.json)
python manage.py install gemini-cli
# Expected: Skips install
#           Shows: "ℹ sequential-thinking already configured"
#           Prompts: "Configure Context7? [Y/n]"

# Test 5: Force reinstall
python manage.py install gemini-cli --force
# Expected: "⚠ Reinstalling Gemini CLI (--force flag used)"
#           Reinstalls npm package
#           Still checks MCP configuration (doesn't reconfigure existing)
```

---

## Task 5: Make MCP Toolbox Installation Idempotent

### 5.1 Modify `install_mcp_toolbox()` Function

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Lines**: 1073-1164

**Changes**:

```python
@install.command(name="mcp-toolbox")
@click.option("--force", is_flag=True, help="Force reinstall even if already installed")
@click.option("--version", default="v0.16.0", help="Specific version to install (default: v0.16.0)")
def install_mcp_toolbox(force: bool, version: str) -> None:
    """Install MCP Toolbox for Databases.

    Idempotent: Safe to run multiple times. Skips installation if MCP Toolbox
    is already installed unless --force flag is used.

    Open-source MCP server for databases (AlloyDB, Spanner, Cloud SQL, etc.)
    Requires Go 1.21 or higher for installation from source.

    Binary downloads available for Linux, macOS (Intel/ARM), and Windows.
    """
    console.print("[yellow]📦 Checking MCP Toolbox installation...[/yellow]")
    console.print()

    # Check if already installed
    is_installed, version_str = is_tool_installed("toolbox")
    if is_installed and not force:
        console.print(f"[green]✓ MCP Toolbox already installed[/green]")
        toolbox_path = shutil.which("toolbox")
        console.print(f"[dim]  Location: {toolbox_path}[/dim]")
        console.print("[dim]  Use --force to reinstall[/dim]")
        return

    # If force flag, show warning
    if is_installed and force:
        console.print(f"[yellow]⚠ Reinstalling MCP Toolbox (--force flag used)[/yellow]")
        console.print()

    console.print("[yellow]📦 Installing MCP Toolbox for Databases...[/yellow]")
    console.print()

    # ... rest of existing installation logic ...
```

**Note**: Remove `--if-missing` flag (idempotency is now default)

### 5.2 Test MCP Toolbox Re-installation Behavior

**Test Script**:
```bash
# Test 1: Fresh install
python manage.py install mcp-toolbox
# Expected: Downloads and installs binary

# Test 2: Re-run install (should skip)
python manage.py install mcp-toolbox
# Expected: "✓ MCP Toolbox already installed"
#           "Use --force to reinstall"

# Test 3: Force reinstall
python manage.py install mcp-toolbox --force
# Expected: "⚠ Reinstalling MCP Toolbox (--force flag used)"
#           Downloads and reinstalls
```

---

## Task 6: Improve MCP Configuration Functions

### 6.1 Update `configure_gemini_mcp_sqlcl()` Function

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`
**Lines**: 316-366

**Changes**:

```python
def configure_gemini_mcp_sqlcl() -> bool:
    """Configure SQLcl as a Gemini MCP server.

    Returns:
        bool: True if configuration was successful or already exists, False otherwise

    Adds or updates SQLcl MCP server configuration in ~/.gemini/settings.json.
    Configuration format:
    {
        "mcpServers": {
            "sqlcl": {
                "command": "sql",
                "args": ["-mcp"]
            }
        }
    }
    """
    import json

    # Check if already configured
    if is_mcp_server_configured("sqlcl"):
        return True  # Already configured, no need to modify

    gemini_settings_path = Path.home() / ".gemini" / "settings.json"

    # Check if Gemini settings directory exists
    if not gemini_settings_path.parent.exists():
        try:
            gemini_settings_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            return False

    # Read existing settings or create new
    settings: dict[str, Any] = {}
    if gemini_settings_path.exists():
        try:
            with open(gemini_settings_path) as f:
                settings = json.load(f)
        except Exception:
            return False

    # Ensure mcpServers key exists
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    # Add or update SQLcl configuration
    settings["mcpServers"]["sqlcl"] = {"command": "sql", "args": ["-mcp"]}

    # Write back to file
    try:
        with open(gemini_settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False
```

---

## Task 7: Update Connection Name References

### 7.1 Update docs/guides/gemini-mcp-integration.md

**File**: `/home/cody/code/g/oracledb-vertexai-demo/docs/guides/gemini-mcp-integration.md`
**Lines to change**: 108-109, 361

**Changes**:

**Line 108-109 (Before)**:
```markdown
# Creates SQLcl saved connection (note the // before host):
conn -save mcp_demo -savepwd app/super-secret@//localhost:1521/freepdb1
```

**Line 108-109 (After)**:
```markdown
# Creates SQLcl saved connection (note the // before host):
conn -save cymbal_coffee -savepwd app/super-secret@//localhost:1521/freepdb1
```

**Line 361 (Before)**:
```markdown
# Verify saved connection works
sql mcp_demo
```

**Line 361 (After)**:
```markdown
# Verify saved connection works
sql cymbal_coffee
```

**Add new section after line 361**:
```markdown

### Connection Name Migration

**Note**: The default SQLcl connection name was changed from `mcp_demo` to `cymbal_coffee`
to match the project branding (Cymbal Coffee demo application).

**Automatic Migration**: If you have an existing `mcp_demo` connection, the installer will
automatically detect and migrate it to `cymbal_coffee` when you run:

```bash
python3 manage.py install sqlcl
```

**Manual Migration**: To manually create the new connection:

```bash
# Connect using credentials from .env
sql /nolog

# Save with new name (replace with your actual credentials)
SQL> conn -save cymbal_coffee -savepwd app/password@//localhost:1521/freepdb1

# Test the connection
SQL> conn cymbal_coffee
```

The old `mcp_demo` connection can be safely deleted after migration.
```

### 7.2 Add Migration Notes to README or Setup Guide

**Consider adding to**: README.md or a new MIGRATION.md file

**Content**:
```markdown
## Migration Notes

### SQLcl Connection Name Change (2025-10)

The default SQLcl saved connection name has changed from `mcp_demo` to `cymbal_coffee`
to better align with the project branding.

**What this means for you**:
- New installations will use `cymbal_coffee` by default
- Existing `mcp_demo` connections will be automatically migrated
- The migration happens automatically when you run `python manage.py install sqlcl`
- Both connection names will work during the transition period

**No action required** - the migration is automatic and transparent.
```

---

## Task 8: Testing

### 8.1 Test Fresh Installation Flow

**Script**: `/home/cody/code/g/oracledb-vertexai-demo/specs/active/idempotent-install-commands/tmp/test-fresh-install.sh`

```bash
#!/bin/bash
# Test fresh installation flow

set -e

echo "=== Test 1: Fresh Installation ==="

# Clean up any existing installations (for testing only)
# WARNING: This will remove installed tools!
rm -rf ~/.local/bin/uv
rm -rf ~/.local/bin/sql*
npm uninstall -g @google/gemini-cli 2>/dev/null || true

echo "Step 1: Install UV"
python manage.py install uv
# Expected: Installs UV successfully

echo "Step 2: Install SQLcl"
python manage.py install sqlcl
# Expected: Installs SQLcl, creates cymbal_coffee connection

echo "Step 3: Install Gemini CLI"
python manage.py install gemini-cli
# Expected: Installs Gemini CLI, detects SQLcl, configures MCP

echo "=== Fresh Installation Test PASSED ==="
```

### 8.2 Test Re-installation (Should Skip)

**Script**: `/home/cody/code/g/oracledb-vertexai-demo/specs/active/idempotent-install-commands/tmp/test-reinstall.sh`

```bash
#!/bin/bash
# Test re-installation behavior (should skip)

set -e

echo "=== Test 2: Re-installation (Idempotency) ==="

echo "Step 1: Re-install UV (should skip)"
output=$(python manage.py install uv 2>&1)
if echo "$output" | grep -q "already installed"; then
    echo "✓ UV correctly skipped re-installation"
else
    echo "✗ UV did not skip re-installation"
    exit 1
fi

echo "Step 2: Re-install SQLcl (should skip)"
output=$(python manage.py install sqlcl 2>&1)
if echo "$output" | grep -q "already installed"; then
    echo "✓ SQLcl correctly skipped re-installation"
else
    echo "✗ SQLcl did not skip re-installation"
    exit 1
fi

echo "Step 3: Re-install Gemini CLI (should skip)"
output=$(python manage.py install gemini-cli 2>&1)
if echo "$output" | grep -q "already installed"; then
    echo "✓ Gemini CLI correctly skipped re-installation"
else
    echo "✗ Gemini CLI did not skip re-installation"
    exit 1
fi

echo "=== Re-installation Test PASSED ==="
```

### 8.3 Test Cross-Configuration (SQLcl → Gemini)

**Script**: `/home/cody/code/g/oracledb-vertexai-demo/specs/active/idempotent-install-commands/tmp/test-cross-config-sqlcl-first.sh`

```bash
#!/bin/bash
# Test cross-configuration: SQLcl installed first, then Gemini CLI

set -e

echo "=== Test 3: Cross-Configuration (SQLcl → Gemini) ==="

# Clean up
npm uninstall -g @google/gemini-cli 2>/dev/null || true
rm -rf ~/.gemini/settings.json

# Ensure SQLcl is installed
python manage.py install sqlcl

echo "Step 1: Install Gemini CLI (SQLcl already present)"
python manage.py install gemini-cli --yes
# Expected: Detects SQLcl, prompts to configure MCP

# Check if SQLcl MCP server is configured
if grep -q '"sqlcl"' ~/.gemini/settings.json; then
    echo "✓ SQLcl MCP server configured in Gemini settings"
else
    echo "✗ SQLcl MCP server NOT configured"
    exit 1
fi

echo "=== Cross-Configuration (SQLcl → Gemini) Test PASSED ==="
```

### 8.4 Test Cross-Configuration (Gemini → SQLcl)

**Script**: `/home/cody/code/g/oracledb-vertexai-demo/specs/active/idempotent-install-commands/tmp/test-cross-config-gemini-first.sh`

```bash
#!/bin/bash
# Test cross-configuration: Gemini CLI installed first, then SQLcl

set -e

echo "=== Test 4: Cross-Configuration (Gemini → SQLcl) ==="

# Clean up SQLcl
rm -rf ~/.local/bin/sql*
rm -rf ~/.sqlcl

# Ensure Gemini CLI is installed
python manage.py install gemini-cli

echo "Step 1: Install SQLcl (Gemini already present)"
python manage.py install sqlcl
# Expected: Configures SQLcl MCP automatically

# Check if SQLcl MCP server is configured
if grep -q '"sqlcl"' ~/.gemini/settings.json; then
    echo "✓ SQLcl MCP server configured in Gemini settings"
else
    echo "✗ SQLcl MCP server NOT configured"
    exit 1
fi

# Check if cymbal_coffee connection exists
if sql -L | grep -q "cymbal_coffee"; then
    echo "✓ cymbal_coffee connection configured"
else
    echo "✗ cymbal_coffee connection NOT configured"
    exit 1
fi

echo "=== Cross-Configuration (Gemini → SQLcl) Test PASSED ==="
```

### 8.5 Test Connection Migration

**Script**: `/home/cody/code/g/oracledb-vertexai-demo/specs/active/idempotent-install-commands/tmp/test-connection-migration.sh`

```bash
#!/bin/bash
# Test SQLcl connection migration from mcp_demo to cymbal_coffee

set -e

echo "=== Test 5: Connection Migration ==="

# Create old connection name
sql /nolog <<EOF
conn -save mcp_demo -savepwd app/super-secret@//localhost:1521/freepdb1
exit
EOF

echo "Step 1: Verify old connection exists"
if sql -L | grep -q "mcp_demo"; then
    echo "✓ Old connection 'mcp_demo' exists"
else
    echo "✗ Could not create old connection"
    exit 1
fi

echo "Step 2: Run install (should trigger migration)"
python manage.py install sqlcl
# Expected: Migrates mcp_demo to cymbal_coffee

echo "Step 3: Verify new connection exists"
if sql -L | grep -q "cymbal_coffee"; then
    echo "✓ New connection 'cymbal_coffee' exists"
else
    echo "✗ Migration did not create new connection"
    exit 1
fi

echo "=== Connection Migration Test PASSED ==="
```

### 8.6 Test --force Flag Behavior

**Script**: `/home/cody/code/g/oracledb-vertexai-demo/specs/active/idempotent-install-commands/tmp/test-force-flag.sh`

```bash
#!/bin/bash
# Test --force flag behavior

set -e

echo "=== Test 6: --force Flag Behavior ==="

echo "Step 1: Re-install UV with --force"
output=$(python manage.py install uv --force 2>&1)
if echo "$output" | grep -q "Reinstalling"; then
    echo "✓ UV correctly reinstalled with --force flag"
else
    echo "✗ UV did not reinstall with --force flag"
    exit 1
fi

echo "Step 2: Re-install SQLcl with --force"
output=$(python manage.py install sqlcl --force 2>&1)
if echo "$output" | grep -q "Reinstalling"; then
    echo "✓ SQLcl correctly reinstalled with --force flag"
else
    echo "✗ SQLcl did not reinstall with --force flag"
    exit 1
fi

echo "=== --force Flag Test PASSED ==="
```

---

## Task 9: Documentation

### 9.1 Update Install Command Docstrings

**File**: `/home/cody/code/g/oracledb-vertexai-demo/manage.py`

**Changes**:

Already covered in Task 2.1, 3.1, 4.1, 5.1 above.

### 9.2 Update gemini-mcp-integration.md Guide

**File**: `/home/cody/code/g/oracledb-vertexai-demo/docs/guides/gemini-mcp-integration.md`

Already covered in Task 7.1 above.

### 9.3 Add Idempotency Documentation

**File**: Consider adding to README.md or creating a new installation guide

**Content**:
```markdown
## Installation Idempotency

All installation commands are **idempotent** - safe to run multiple times without side effects.

### Behavior

When you run an installation command:

1. **Check**: Verifies if tool is already installed
2. **Skip**: If installed, displays current version and skips installation
3. **Install**: Only installs if tool is not present
4. **Force**: Use `--force` flag to reinstall even if present

### Examples

```bash
# First run: Installs UV
python manage.py install uv
# Output: "📦 Installing UV package manager..."
#         "✓ UV installed successfully!"

# Second run: Skips installation
python manage.py install uv
# Output: "✓ UV already installed: uv 0.5.15"
#         "Use --force to reinstall"

# Force reinstall
python manage.py install uv --force
# Output: "⚠ Reinstalling UV (--force flag used)"
#         "✓ UV installed successfully!"
```

### Cross-Configuration

Installing one tool can automatically configure related tools:

**Scenario 1: Install SQLcl when Gemini CLI exists**
```bash
python manage.py install gemini-cli  # Installs Gemini CLI
python manage.py install sqlcl       # Installs SQLcl AND configures Gemini MCP
```

**Scenario 2: Install Gemini CLI when SQLcl exists**
```bash
python manage.py install sqlcl       # Installs SQLcl
python manage.py install gemini-cli  # Installs Gemini AND prompts to configure SQLcl MCP
```

### Connection Name Change

The default SQLcl connection name changed from `mcp_demo` to `cymbal_coffee`.

- **Automatic migration**: Old connections are automatically detected and migrated
- **No manual action required**: The installer handles the migration
- **Custom names**: Use `--connection-name` to specify a different name

```bash
# Uses default name "cymbal_coffee"
python manage.py install sqlcl

# Uses custom name
python manage.py install sqlcl --connection-name my_database
```
```

---

## Task 10: Validation & Cleanup

### 10.1 Verification Checklist

**Run through all scenarios**:

- [ ] Fresh install of UV → Works
- [ ] Re-run UV install → Skips gracefully
- [ ] Fresh install of SQLcl → Creates cymbal_coffee connection
- [ ] Re-run SQLcl install → Skips, checks MCP config
- [ ] Fresh install of Gemini CLI → Works
- [ ] Re-run Gemini CLI install → Skips, checks MCP config
- [ ] Install SQLcl then Gemini → Cross-configures MCP
- [ ] Install Gemini then SQLcl → Cross-configures MCP
- [ ] Migration from mcp_demo → cymbal_coffee works
- [ ] --force flag reinstalls correctly
- [ ] Makefile targets are idempotent
- [ ] Documentation is accurate and complete

### 10.2 Code Quality Checks

**Run linters and formatters**:
```bash
# Format code
uv run ruff check --fix manage.py

# Run tests
uv run pytest tests/

# Check for issues
uv run mypy manage.py
```

### 10.3 Clean Up Test Files

**After testing**:
```bash
# Remove test scripts
rm -rf specs/active/idempotent-install-commands/tmp/test-*.sh

# Keep only documentation files in requirement folder
ls specs/active/idempotent-install-commands/
# Expected: prd.md, tasks.md, tasks-detail.md, recovery.md, progress.md
```

---

## Summary

**Total Tasks**: 10 major tasks, ~40 subtasks

**Implementation Order**:
1. Utility functions (foundation)
2. UV idempotency (simplest)
3. SQLcl idempotency + connection migration
4. Gemini CLI idempotency + MCP re-configuration
5. MCP Toolbox idempotency
6. MCP configuration improvements
7. Connection name updates
8. Comprehensive testing
9. Documentation updates
10. Final validation

**Estimated Time**: 4-6 hours total

**Files Modified**:
- `manage.py` (primary implementation)
- `Makefile` (idempotent targets)
- `docs/guides/gemini-mcp-integration.md` (connection name updates)

**Lines of Code**: ~200-300 LOC (modifications + new utility functions)

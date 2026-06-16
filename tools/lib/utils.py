# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Shared utility functions for CLI tools."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()


def detect_deployment_mode() -> str:
    """Detect deployment mode from environment.

    Returns:
        str: "managed" or "external"

    Detection logic:
        - If DATABASE_HOST or DATABASE_URL is set -> external
        - Otherwise -> managed (Docker container we control)

    Wallet detection is automatic - if TNS_ADMIN/WALLET_LOCATION is set,
    wallet-based connection will be used regardless of mode.
    """
    if os.getenv("DATABASE_HOST") or os.getenv("DATABASE_URL"):
        return "external"
    return "managed"


def check_env_file() -> bool:
    """Check if .env file exists."""
    return Path(".env").exists()


def generate_secret_key() -> str:
    """Generate a secure random secret key."""
    import secrets

    return secrets.token_hex(32)


def create_env_interactive(mode: str, non_interactive: bool = False) -> bool:  # noqa: C901, PLR0914
    """Create .env file interactively based on deployment mode.

    Args:
        mode: Deployment mode ("managed" or "external")
        non_interactive: If True, use defaults without prompting

    Returns:
        bool: True if successful, False otherwise
    """
    env_path = Path(".env")

    if env_path.exists():
        console.print("[yellow]⚠ .env already exists[/yellow]")
        if not non_interactive:
            overwrite = Confirm.ask("Overwrite existing .env?", default=False)
            if not overwrite:
                console.print("[cyan]Keeping existing .env[/cyan]")
                return True

    console.print(f"[bold]Creating .env for [cyan]{mode}[/cyan] mode...[/bold]")
    console.print()

    # Core application settings (always required)
    default_secret = generate_secret_key()
    if non_interactive:
        secret_key = default_secret
        google_project = "demo-project"
        google_api_key = ""
        google_creds = ""
    else:
        console.print("[bold]Core Application Settings:[/bold]")
        secret_key = Prompt.ask("SECRET_KEY (press Enter to auto-generate)", default=default_secret, show_default=False)
        console.print()

        console.print("[bold]Google Cloud / Vertex AI Settings:[/bold]")
        google_project = Prompt.ask("GOOGLE_PROJECT_ID", default="demo-project")
        google_api_key = Prompt.ask("GOOGLE_API_KEY (optional)", default="")
        google_creds = Prompt.ask("GOOGLE_APPLICATION_CREDENTIALS (optional)", default="")

    env_content = "# App\n"

    if mode == "managed":
        if non_interactive:
            db_user = "app"
            db_password = "SuperSecret1"  # noqa: S105
            oee_password = "SuperSecret1"  # noqa: S105
            db_url = f"oracle+oracledb://{db_user}:{db_password}@myatp_low"
            wallet_password = "SuperSecret1"  # noqa: S105
            tns_admin = ".envs/tns"
            db_service = "myatp_low"
        else:
            console.print("[bold]Database Settings (Managed Container):[/bold]")
            db_user = Prompt.ask("DATABASE_USER", default="app")
            db_password = Prompt.ask("DATABASE_PASSWORD", default="SuperSecret1", password=True)
            oee_password = Prompt.ask("OEE_PASSWORD", default=db_password, password=True)
            db_url = Prompt.ask("DATABASE_URL", default=f"oracle+oracledb://{db_user}:{db_password}@myatp_low")
            wallet_password = Prompt.ask("WALLET_PASSWORD", default="SuperSecret1")
            tns_admin = Prompt.ask("TNS_ADMIN", default=".envs/tns")
            db_service = Prompt.ask("DATABASE_SERVICE_NAME", default="myatp_low")

        env_content += "# Database (Managed Container)\n"
        env_content += f"DATABASE_URL={db_url}\n"
        env_content += f"DATABASE_USER={db_user}\n"
        env_content += f"DATABASE_PASSWORD={db_password}\n"
        env_content += f"OEE_PASSWORD={oee_password}\n"
        env_content += f"WALLET_PASSWORD={wallet_password}\n"
        env_content += f"TNS_ADMIN={tns_admin}\n"
        env_content += f"DATABASE_SERVICE_NAME={db_service}\n\n"

    elif non_interactive:
        use_wallet = False
        db_user = "app"
        db_password = "your-password"  # noqa: S105
        db_host = "your-oracle-host"
        db_port = "1521"
        db_service = "your-service-name"
    else:
        console.print("[bold]External Database Connection:[/bold]")
        use_wallet = Confirm.ask("Use wallet-based connection (Autonomous DB, mTLS)?", default=False)

        if use_wallet:
            console.print("[dim]Using DATABASE_URL format for wallet connections[/dim]")
            db_url = Prompt.ask("DATABASE_URL", default="oracle+oracledb://ADMIN:password@service_high")
            wallet_password = Prompt.ask("WALLET_PASSWORD", default="")
            wallet_location = Prompt.ask("WALLET_LOCATION/TNS_ADMIN", default="./.envs/tns")

            env_content += "# Database (External - Wallet/Autonomous)\n"
            env_content += f"DATABASE_URL={db_url}\n"
            if wallet_password:
                env_content += f"WALLET_PASSWORD={wallet_password}\n"
            env_content += f"TNS_ADMIN={wallet_location}\n\n"
        else:
            console.print("[dim]Using standard connection parameters[/dim]")
            db_user = Prompt.ask("DATABASE_USER", default="app")
            db_password = Prompt.ask("DATABASE_PASSWORD", default="your-password")
            db_host = Prompt.ask("DATABASE_HOST", default="your-oracle-host")
            db_port = Prompt.ask("DATABASE_PORT", default="1521")
            db_service = Prompt.ask("DATABASE_SERVICE_NAME", default="your-service-name")

            env_content += "# Database (External - Standard)\n"
            env_content += f"DATABASE_USER={db_user}\n"
            env_content += f"DATABASE_PASSWORD={db_password}\n"
            env_content += f"DATABASE_HOST={db_host}\n"
            env_content += f"DATABASE_PORT={db_port}\n"
            env_content += f"DATABASE_SERVICE_NAME={db_service}\n\n"

    # Google Cloud / Vertex AI settings
    env_content += "# APIs\n"
    if google_creds:
        env_content += f"GOOGLE_APPLICATION_CREDENTIALS={google_creds}\n"
    env_content += f"GOOGLE_PROJECT_ID={google_project}\n"
    if google_api_key:
        env_content += f"GOOGLE_API_KEY={google_api_key}\n"
    env_content += "VERTEX_AI_PROJECT_ID=${GOOGLE_PROJECT_ID}\n\n"

    # Server settings
    env_content += "# server\n"
    env_content += "LITESTAR_DEBUG=true\n"
    env_content += "LITESTAR_HOST=0.0.0.0\n"
    env_content += "LITESTAR_PORT=5006\n"
    env_content += "LITESTAR_GRANIAN_IN_SUBPROCESS=false\n"
    env_content += "LITESTAR_GRANIAN_USE_LITESTAR_LOGGER=true\n"
    env_content += f"SECRET_KEY={secret_key}\n\n"

    # Development settings
    env_content += "# only in development\n"
    env_content += "VITE_DEV_MODE=False\n"

    try:
        env_path.write_text(env_content, encoding="utf-8")
        console.print("[green]✓ Created .env file[/green]")
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]✗ Failed to create .env: {e}[/red]")
        return False
    else:
        return True


def run_command(cmd: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
        )
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)
    else:
        return result.returncode, result.stdout, result.stderr


def is_tool_installed(tool_name: str, version_flag: str = "--version") -> tuple[bool, str]:
    """Check if a tool is installed and available in PATH.

    Args:
        tool_name: Name of the executable to check (e.g., 'uv', 'sql')
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
    except Exception:  # noqa: BLE001, S110
        pass

    return False, ""


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
        with gemini_settings_path.open() as f:
            settings = json.load(f)
        mcp_servers = settings.get("mcpServers", {})
        # Check if server exists and is not None/null
        return server_name in mcp_servers and mcp_servers[server_name] is not None
    except Exception:  # noqa: BLE001
        return False


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
            ["sql", "-L"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:  # noqa: BLE001
        return False
    else:
        # Check if connection_name appears in the output
        return connection_name in result.stdout


def configure_sqlcl_connection_with_password(connection_name: str = "cymbal_coffee") -> tuple[bool, str]:  # noqa: PLR0911
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

    # Load .env values
    env_path = Path(".env")
    if not env_path.exists():
        return False, ".env file not found - run 'python manage.py init' first"

    env_vars = dotenv_values(env_path)

    # Get connection parameters
    user = env_vars.get("DATABASE_USER")
    password = env_vars.get("DATABASE_PASSWORD")
    host = env_vars.get("DATABASE_HOST")
    port = env_vars.get("DATABASE_PORT", "1521")
    service_name = env_vars.get("DATABASE_SERVICE_NAME")

    # Validate required parameters
    if not user:
        return False, "DATABASE_USER not configured in .env"
    if not password:
        return False, "DATABASE_PASSWORD not configured in .env"
    if not host:
        return False, "DATABASE_HOST not configured in .env"
    if not service_name:
        return False, "DATABASE_SERVICE_NAME not configured in .env"

    # Check if SQLcl is installed
    if not shutil.which("sql"):
        return False, "SQLcl not found in PATH - run 'python manage.py install sqlcl' first"

    # Build connection string (Oracle format with //)
    conn_string = f"{user}/{password}@//{host}:{port}/{service_name}"

    # Use echo to pipe the connection command
    conn_cmd = f"conn -save {connection_name} -savepwd {conn_string}\nexit"

    try:
        result = subprocess.run(
            ["sql", "/nolog"],  # noqa: S607
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

    except subprocess.TimeoutExpired:
        return False, "SQLcl command timed out"
    except Exception as e:  # noqa: BLE001
        return False, f"Error running SQLcl: {e}"
    else:
        return False, f"Failed to save connection: {error_msg}"


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
    # Check if already configured
    if is_mcp_server_configured("sqlcl"):
        return True  # Already configured, no need to modify

    gemini_settings_path = Path.home() / ".gemini" / "settings.json"

    # Check if Gemini settings directory exists
    if not gemini_settings_path.parent.exists():
        try:
            gemini_settings_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001
            return False

    # Read existing settings or create new
    settings: dict[str, Any] = {}
    if gemini_settings_path.exists():
        try:
            with gemini_settings_path.open() as f:
                settings = json.load(f)
        except Exception:  # noqa: BLE001
            return False

    # Ensure mcpServers key exists
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    # Add or update SQLcl configuration
    settings["mcpServers"]["sqlcl"] = {"command": "sql", "args": ["-mcp"]}

    # Write back to file
    try:
        with gemini_settings_path.open("w") as f:
            json.dump(settings, f, indent=2)
    except Exception:  # noqa: BLE001
        return False
    else:
        return True

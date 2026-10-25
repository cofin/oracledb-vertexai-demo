# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Shared utility functions for CLI tools."""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal

from rich.console import Console
from rich.prompt import Confirm, Prompt

from app.utils.serialization import decode_json, format_json

__all__ = (
    "MCP_TOOLBOX_ORACLE_SERVER_NAME",
    "SQLCL_MCP_SERVER_NAME",
    "AntigravityMCPConfigTarget",
    "build_antigravity_mcp_config",
    "build_mcp_toolbox_oracle_server_config",
    "build_sqlcl_mcp_server_config",
    "check_env_file",
    "console",
    "create_env_interactive",
    "detect_deployment_mode",
    "generate_secret_key",
    "get_antigravity_mcp_config_path",
    "is_tool_installed",
    "run_command",
    "write_antigravity_mcp_config",
)

console = Console()

AntigravityMCPConfigTarget = Literal["workspace", "ide", "cli-global"]
SQLCL_MCP_SERVER_NAME = "sqlcl"
MCP_TOOLBOX_ORACLE_SERVER_NAME = "oracle-toolbox"

_DEFAULT_MANAGED_PASSWORD = "SuperSecret1"  # ruff: ignore[hardcoded-password-string]
_DEFAULT_EXTERNAL_PASSWORD = "your-password"  # ruff: ignore[hardcoded-password-string]
_SECRET_KEY_BYTES = 32


def detect_deployment_mode() -> str:
    """Detect deployment mode from environment variables.

    Honors explicit ``DATABASE_DEPLOYMENT_MODE`` (``"managed"`` or ``"external"``)
    before checking ``DATABASE_HOST`` or ``DATABASE_URL``.
    """
    explicit = os.getenv("DATABASE_DEPLOYMENT_MODE", "").strip().lower()
    if explicit in {"managed", "external"}:
        return explicit
    if os.getenv("DATABASE_HOST") or os.getenv("DATABASE_URL"):
        return "external"
    return "managed"


def check_env_file() -> bool:
    """Return True when a ``.env`` file exists in the current working directory."""
    return Path(".env").exists()


def generate_secret_key() -> str:
    """Generate a cryptographically random 32-byte hex secret key."""
    return secrets.token_hex(_SECRET_KEY_BYTES)


def create_env_interactive(mode: str, non_interactive: bool = False) -> bool:
    """Create a ``.env`` file interactively or using defaults for the chosen mode."""
    env_path = Path(".env")
    if env_path.exists():
        console.print("[yellow]⚠ .env already exists[/yellow]")
        if not non_interactive and not Confirm.ask("Overwrite existing .env?", default=False):
            console.print("[cyan]Keeping existing .env[/cyan]")
            return True

    console.print(f"[bold]Creating .env for [cyan]{mode}[/cyan] mode...[/bold]")
    console.print()

    secret_key, google_project, google_api_key, google_creds = _prompt_core_settings(non_interactive=non_interactive)
    db_section = (
        _build_managed_db_section(non_interactive=non_interactive)
        if mode == "managed"
        else _build_external_db_section(non_interactive=non_interactive)
    )
    env_content = _render_env_document(
        db_section=db_section,
        secret_key=secret_key,
        google_project=google_project,
        google_api_key=google_api_key,
        google_creds=google_creds,
    )

    try:
        env_path.write_text(env_content, encoding="utf-8")
        console.print("[green]✓ Created .env file[/green]")
    except Exception as exc:
        console.print(f"[red]✗ Failed to create .env: {exc}[/red]")
        return False
    return True


def run_command(cmd: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run a command and return ``(returncode, stdout, stderr)``."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.stdout, exc.stderr
    except Exception as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout, result.stderr


def is_tool_installed(tool_name: str, version_flag: str = "--version") -> tuple[bool, str]:
    """Check whether an executable is available in ``PATH`` and responds to ``version_flag``."""
    if not shutil.which(tool_name):
        return False, ""

    returncode, stdout, _ = run_command([tool_name, version_flag], check=False)
    if returncode == 0:
        return True, stdout.strip()
    return False, ""


def get_antigravity_mcp_config_path(
    target: AntigravityMCPConfigTarget = "workspace", *, workspace_root: Path | None = None, home: Path | None = None
) -> Path:
    """Return the Antigravity MCP config path for the requested target."""
    if target == "workspace":
        return (workspace_root or Path.cwd()) / ".agents" / "mcp_config.json"

    home_path = home or Path.home()
    if target == "ide":
        return home_path / ".gemini" / "config" / "mcp_config.json"
    return home_path / ".gemini" / "antigravity-cli" / "mcp_config.json"


def build_sqlcl_mcp_server_config() -> dict[str, Any]:
    """Build SQLcl MCP server config without embedding local credentials."""
    return {"command": "sql", "args": ["-mcp"]}


def build_mcp_toolbox_oracle_server_config() -> dict[str, Any]:
    """Build MCP Toolbox Oracle config with environment placeholders only."""
    return {
        "command": "toolbox",
        "args": ["--prebuilt", "oracledb", "--stdio"],
        "env": {
            "ORACLE_CONNECTION_STRING": "${ORACLE_CONNECTION_STRING}",
            "ORACLE_USERNAME": "${ORACLE_USERNAME}",
            "ORACLE_PASSWORD": "${ORACLE_PASSWORD}",
            "ORACLE_WALLET": "${ORACLE_WALLET}",
            "ORACLE_USE_OCI": "${ORACLE_USE_OCI}",
        },
    }


def build_antigravity_mcp_config(*, include_sqlcl: bool = True, include_mcp_toolbox: bool = True) -> dict[str, Any]:
    """Build an Antigravity MCP config document for this demo."""
    mcp_servers: dict[str, Any] = {}
    if include_sqlcl:
        mcp_servers[SQLCL_MCP_SERVER_NAME] = build_sqlcl_mcp_server_config()
    if include_mcp_toolbox:
        mcp_servers[MCP_TOOLBOX_ORACLE_SERVER_NAME] = build_mcp_toolbox_oracle_server_config()
    return {"mcpServers": mcp_servers}


def write_antigravity_mcp_config(
    target: AntigravityMCPConfigTarget = "workspace",
    *,
    workspace_root: Path | None = None,
    home: Path | None = None,
    include_sqlcl: bool = True,
    include_mcp_toolbox: bool = True,
) -> Path:
    """Merge this demo's MCP servers into an Antigravity MCP config file."""
    config_path = get_antigravity_mcp_config_path(target, workspace_root=workspace_root, home=home)
    generated = build_antigravity_mcp_config(include_sqlcl=include_sqlcl, include_mcp_toolbox=include_mcp_toolbox)

    existing: dict[str, Any] = {}
    if config_path.exists():
        loaded = decode_json(config_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            existing = loaded

    existing_mcp_servers = existing.setdefault("mcpServers", {})
    if not isinstance(existing_mcp_servers, dict):
        existing_mcp_servers = {}
        existing["mcpServers"] = existing_mcp_servers
    existing_mcp_servers.update(generated["mcpServers"])

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(f"{format_json(existing, indent=2)}\n", encoding="utf-8")
    return config_path


def _prompt_core_settings(*, non_interactive: bool) -> tuple[str, str, str, str]:
    """Return ``(secret_key, google_project, google_api_key, google_creds)``."""
    default_secret = generate_secret_key()
    if non_interactive:
        return default_secret, "demo-project", "", ""

    console.print("[bold]Core Application Settings:[/bold]")
    secret_key = Prompt.ask("SECRET_KEY (press Enter to auto-generate)", default=default_secret, show_default=False)
    console.print()

    console.print("[bold]Google Cloud / Vertex AI Settings:[/bold]")
    google_project = Prompt.ask("GOOGLE_PROJECT_ID", default="demo-project")
    google_api_key = Prompt.ask("GOOGLE_API_KEY (optional)", default="")
    google_creds = Prompt.ask("GOOGLE_APPLICATION_CREDENTIALS (optional)", default="")
    return secret_key, google_project, google_api_key, google_creds


def _build_managed_db_section(*, non_interactive: bool) -> str:
    """Render ``.env`` lines for the managed ``adb-free:latest-26ai`` container."""
    if non_interactive:
        db_user = "app"
        db_password = _DEFAULT_MANAGED_PASSWORD
        db_url = "myatp_low"
        wallet_location = "./.envs/tns"
        wallet_password = _DEFAULT_MANAGED_PASSWORD
    else:
        console.print("[bold]Database Settings (Managed ADB-Free 26ai Container):[/bold]")
        db_user = Prompt.ask("DATABASE_USER", default="app")
        db_password = Prompt.ask("DATABASE_PASSWORD", default=_DEFAULT_MANAGED_PASSWORD, password=True)
        db_url = Prompt.ask("DATABASE_URL", default="myatp_low")
        wallet_location = Prompt.ask("WALLET_LOCATION", default="./.envs/tns")
        wallet_password = Prompt.ask("WALLET_PASSWORD", default=_DEFAULT_MANAGED_PASSWORD, password=True)

    return (
        "# Database (Managed ADB-Free 26ai Container)\n"
        "DATABASE_DEPLOYMENT_MODE=managed\n"
        f"DATABASE_USER={db_user}\n"
        f"DATABASE_PASSWORD={db_password}\n"
        f"DATABASE_URL={db_url}\n"
        f"WALLET_LOCATION={wallet_location}\n"
        f"WALLET_PASSWORD={wallet_password}\n\n"
    )


def _build_external_db_section(*, non_interactive: bool) -> str:
    """Render ``.env`` lines for an external standard or wallet-backed Oracle 26ai database."""
    if non_interactive:
        return (
            "# Database (External - Standard)\n"
            "DATABASE_DEPLOYMENT_MODE=external\n"
            "DATABASE_USER=app\n"
            f"DATABASE_PASSWORD={_DEFAULT_EXTERNAL_PASSWORD}\n"
            "DATABASE_HOST=your-oracle-host\n"
            "DATABASE_PORT=1521\n"
            "DATABASE_SERVICE_NAME=your-service-name\n\n"
        )

    console.print("[bold]External Database Connection:[/bold]")
    use_wallet = Confirm.ask("Use wallet-based connection (Autonomous DB, mTLS)?", default=False)
    if use_wallet:
        console.print("[dim]Using DATABASE_URL and WALLET_LOCATION for wallet connections[/dim]")
        db_url = Prompt.ask("DATABASE_URL", default="myatp_low")
        db_user = Prompt.ask("DATABASE_USER", default="app")
        db_password = Prompt.ask("DATABASE_PASSWORD", default=_DEFAULT_EXTERNAL_PASSWORD, password=True)
        wallet_location = Prompt.ask("WALLET_LOCATION", default="./.envs/tns")
        wallet_password = Prompt.ask("WALLET_PASSWORD", default="")
        lines = [
            "# Database (External - Wallet/Autonomous)",
            "DATABASE_DEPLOYMENT_MODE=external",
            f"DATABASE_USER={db_user}",
            f"DATABASE_PASSWORD={db_password}",
            f"DATABASE_URL={db_url}",
            f"WALLET_LOCATION={wallet_location}",
        ]
        if wallet_password:
            lines.append(f"WALLET_PASSWORD={wallet_password}")
        return "\n".join(lines) + "\n\n"

    console.print("[dim]Using standard connection parameters[/dim]")
    db_user = Prompt.ask("DATABASE_USER", default="app")
    db_password = Prompt.ask("DATABASE_PASSWORD", default=_DEFAULT_EXTERNAL_PASSWORD)
    db_host = Prompt.ask("DATABASE_HOST", default="your-oracle-host")
    db_port = Prompt.ask("DATABASE_PORT", default="1521")
    db_service = Prompt.ask("DATABASE_SERVICE_NAME", default="your-service-name")
    return (
        "# Database (External - Standard)\n"
        "DATABASE_DEPLOYMENT_MODE=external\n"
        f"DATABASE_USER={db_user}\n"
        f"DATABASE_PASSWORD={db_password}\n"
        f"DATABASE_HOST={db_host}\n"
        f"DATABASE_PORT={db_port}\n"
        f"DATABASE_SERVICE_NAME={db_service}\n\n"
    )


def _render_env_document(
    *, db_section: str, secret_key: str, google_project: str, google_api_key: str, google_creds: str
) -> str:
    """Assemble the complete ``.env`` file payload."""
    api_lines = ["# APIs"]
    if google_creds:
        api_lines.append(f"GOOGLE_APPLICATION_CREDENTIALS={google_creds}")
    api_lines.append(f"GOOGLE_PROJECT_ID={google_project}")
    if google_api_key:
        api_lines.append(f"GOOGLE_API_KEY={google_api_key}")
    api_lines.extend([
        "VERTEX_AI_PROJECT_ID=${GOOGLE_PROJECT_ID}",
        "VERTEX_AI_LOCATION=global",
        "",
        "# server",
        "LITESTAR_DEBUG=true",
        "LITESTAR_HOST=0.0.0.0",
        "LITESTAR_PORT=8000",
        f"SECRET_KEY={secret_key}",
        "",
        "# only in development",
        "VITE_DEV_MODE=False",
        "",
    ])
    return "# App\n" + db_section + "\n".join(api_lines)

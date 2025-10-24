#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.28.1",
#     "rich-click>=1.8.0",
#     "oracledb>=2.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""Unified project management CLI for Oracle + Vertex AI demo.

This tool provides a single interface for:
- Project initialization and environment setup
- Prerequisite installation (UV, SQLcl, etc.)
- Oracle database deployment (managed container or external connection)
- Wallet configuration and validation (auto-detected)
- Connection testing and health checks

IMPORTANT: This is a development tool and should not be shipped with production code.

Usage:
    python manage.py init                  # Initialize project
    python manage.py install all          # Install all prerequisites
    python manage.py doctor               # Verify setup
    python manage.py database start       # Start Oracle container
    python manage.py --help               # Show all commands
"""

from __future__ import annotations

import sys
from pathlib import Path

import rich_click as click
from rich.console import Console

# Ensure tools package is importable
sys.path.insert(0, str(Path(__file__).parent))

# Import Oracle CLI command groups (after sys.path setup)
# Import project management CLI commands
from tools.cli import doctor_command, init_command, install_group
from tools.oracle import (
    connect_group as oracle_connect_group,
)
from tools.oracle import (
    database_group as oracle_database_group,
)
from tools.oracle import (
    status_command as oracle_status_command,
)
from tools.oracle import (
    wallet_group as oracle_wallet_group,
)

console = Console()

# Configure rich-click
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "yellow italic"
click.rich_click.ERRORS_SUGGESTION = "Try running the '--help' flag for more information."


# ============================================================================
# Main CLI Group
# ============================================================================


@click.group()
@click.version_option(version="0.1.0", prog_name="manage")
def cli() -> None:
    """Unified DevOps CLI for Oracle + Vertex AI Demo.

    This tool manages project initialization, prerequisites, database deployment,
    and configuration across two deployment modes:

    - managed: Oracle 23ai Free container via Docker/Podman (we control it)
    - external: Connect to existing database (auto-detects wallet for mTLS)

    Common workflow:
      1. python manage.py init              # Set up .env
      2. python manage.py install all       # Install prerequisites
      3. python manage.py doctor            # Verify setup
      4. python manage.py database oracle start-local-container  # Start database (managed mode)

    For help on any command:
      python manage.py <command> --help
    """


# ============================================================================
# Register Project Management Commands
# ============================================================================

# Register init command
cli.add_command(init_command, name="init")

# Register install group
cli.add_command(install_group, name="install")

# Register doctor command
cli.add_command(doctor_command, name="doctor")

# Register status command (from Oracle CLI)
cli.add_command(oracle_status_command, name="status")


# ============================================================================
# Register Oracle Database Commands
# ============================================================================


@cli.group(name="database")
def database_cli_group() -> None:
    """Manage database operations.

    Commands for database management across different providers.
    """


@database_cli_group.group(name="oracle")
def oracle_cli_group() -> None:
    """Manage Oracle database operations.

    Commands for deploying and managing Oracle databases, wallets, and connections.
    Requires Docker or Podman for managed mode.
    """


# Register database commands under oracle_cli_group
oracle_cli_group.add_command(oracle_database_group.commands["start"], name="start-local-container")
oracle_cli_group.add_command(oracle_database_group.commands["stop"], name="stop-local-container")
oracle_cli_group.add_command(oracle_database_group.commands["status"], name="status")
oracle_cli_group.add_command(oracle_database_group.commands["logs"], name="local-container-logs")
oracle_cli_group.add_command(oracle_database_group.commands["remove"], name="wipe-local-container")
oracle_cli_group.add_command(oracle_database_group.commands["restart"], name="restart-local-container")

# Register wallet group under oracle_cli_group
oracle_cli_group.add_command(oracle_wallet_group, name="wallet")

# Register connect group under oracle_cli_group
oracle_cli_group.add_command(oracle_connect_group, name="connect")


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

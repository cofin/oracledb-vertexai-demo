# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Database connection testing CLI commands."""

from __future__ import annotations

import rich_click as click
from rich.console import Console

from tools.oracle.connection import ConnectionConfig, ConnectionTester, DeploymentMode

console = Console()


@click.group(name="connect")
def connect_group() -> None:
    """Test database connections.

    Test connectivity to Oracle databases in any deployment mode.
    """


@connect_group.command(name="test")
@click.option(
    "--mode", type=click.Choice(["managed", "external"]), help="Deployment mode (auto-detect if not specified)"
)
@click.option("--timeout", default=10, help="Connection timeout in seconds")
def connect_test(mode: str | None, timeout: int) -> None:
    """Test database connection.

    Attempts to connect and execute a simple query.
    Auto-detects wallet if configured.
    """
    tester = ConnectionTester(console=console)

    try:
        run_connection_test(tester=tester, mode=mode, timeout=timeout)
    except Exception as e:
        if not isinstance(e, click.Abort):
            console.print(f"[red]✗ Test failed: {e}[/red]")
        raise click.Abort from e


def run_connection_test(*, tester: ConnectionTester, mode: str | None, timeout: int) -> None:
    """Build connection config and run the CLI connection test."""
    config = ConnectionConfig.from_env()
    if mode:
        config.mode = DeploymentMode(mode.upper())
    result = tester.test(config, timeout=timeout, display=True)
    if not result.success:
        raise click.Abort


@connect_group.command(name="info")
def connect_info() -> None:
    """Display connection information.

    Shows current connection configuration from environment.
    """
    from tools.oracle.connection import ConnectionTester

    tester = ConnectionTester(console=console)

    try:
        info = tester.get_connection_info()
        tester.display_connection_info(info)
    except Exception as e:
        console.print(f"[red]✗ Failed to get connection info: {e}[/red]")
        raise click.Abort from e

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.28.1",
#     "rich>=13.9.4",
#     "rich-click>=1.8.0",
#     "oracledb>=2.0.0",
# ]
# ///
"""Oracle deployment and management tool.

This unified CLI tool manages Oracle database deployment across two modes:
- Managed: Oracle 23ai Free container via Docker/Podman (we control it)
- External: Connect to existing database (auto-detects wallet for mTLS)

Replaces docker-compose.yml and tools/install_sqlcl.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import rich_click as click
from rich.console import Console

# Ensure tools package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


console = Console()

# Configure rich-click
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True


@click.group()
@click.version_option(version="0.1.0", prog_name="oracle-deploy")
def cli() -> None:
    """Oracle Database Deployment Tool.

    Unified tool for managing Oracle databases across deployment modes:
    - Managed: Local containers (Docker/Podman) we control
    - External: Connect to existing database (auto-detects wallet)
    """


# ============================================================================
# DATABASE COMMANDS (Managed Container Operations)
# ============================================================================


@cli.group(name="database")
def database_group() -> None:
    """Manage Oracle database container (managed mode).

    Commands for deploying and managing Oracle 23ai Free container.
    Requires Docker or Podman to be installed.
    """


@database_group.command(name="start")
@click.option("--pull", is_flag=True, help="Pull latest image before starting")
@click.option("--recreate", is_flag=True, help="Remove and recreate container if exists")
@click.option("--env-file", type=click.Path(exists=True), help="Environment file to load")
def database_start(pull: bool, recreate: bool, env_file: str | None) -> None:
    """Start Oracle database container.

    Deploys Oracle 23 Free container with configuration matching docker-compose.yml.
    """
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import DatabaseConfig, OracleDatabase

    try:
        runtime = ContainerRuntime()
        config = DatabaseConfig.from_env()
        db = OracleDatabase(runtime=runtime, config=config, console=console)

        console.print("[yellow]Starting Oracle database container...[/yellow]")
        db.start(pull=pull, recreate=recreate)
        console.print("[green]✓ Database started successfully![/green]")

    except Exception as e:
        console.print(f"[red]✗ Failed to start database: {e}[/red]")
        raise click.Abort() from e


@database_group.command(name="stop")
@click.option("--timeout", default=30, help="Seconds to wait before forcing stop")
def database_stop(timeout: int) -> None:
    """Stop Oracle database container."""
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import DatabaseConfig, OracleDatabase

    try:
        runtime = ContainerRuntime()
        config = DatabaseConfig.from_env()
        db = OracleDatabase(runtime=runtime, config=config, console=console)

        if not db.is_running():
            console.print("[yellow]Container is not running[/yellow]")
            return

        console.print("[yellow]Stopping Oracle database container...[/yellow]")
        db.stop(timeout=timeout)
        console.print("[green]✓ Database stopped[/green]")

    except Exception as e:
        console.print(f"[red]✗ Failed to stop database: {e}[/red]")
        raise click.Abort() from e


@database_group.command(name="restart")
@click.option("--timeout", default=30, help="Seconds to wait for stop")
def database_restart(timeout: int) -> None:
    """Restart Oracle database container."""
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import DatabaseConfig, OracleDatabase

    try:
        runtime = ContainerRuntime()
        config = DatabaseConfig.from_env()
        db = OracleDatabase(runtime=runtime, config=config, console=console)

        console.print("[yellow]Restarting Oracle database container...[/yellow]")
        db.restart(timeout=timeout)
        console.print("[green]✓ Database restarted[/green]")

    except Exception as e:
        console.print(f"[red]✗ Failed to restart database: {e}[/red]")
        raise click.Abort() from e


@database_group.command(name="remove")
@click.option("--volumes", is_flag=True, help="Also remove associated volumes")
@click.option("--force", is_flag=True, help="Force removal even if running")
@click.confirmation_option(prompt="Are you sure you want to remove the container?")
def database_remove(volumes: bool, force: bool) -> None:
    """Remove Oracle database container."""
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import DatabaseConfig, OracleDatabase

    try:
        runtime = ContainerRuntime()
        config = DatabaseConfig.from_env()
        db = OracleDatabase(runtime=runtime, config=config, console=console)

        console.print("[yellow]Removing Oracle database container...[/yellow]")
        db.remove(remove_volumes=volumes, force=force)
        console.print("[green]✓ Database container removed[/green]")

    except Exception as e:
        console.print(f"[red]✗ Failed to remove database: {e}[/red]")
        raise click.Abort() from e


@database_group.command(name="logs")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--tail", type=int, help="Number of lines to show from end")
@click.option("--since", help="Show logs since timestamp/duration")
def database_logs(follow: bool, tail: int | None, since: str | None) -> None:
    """View database container logs."""
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import DatabaseConfig, OracleDatabase

    try:
        runtime = ContainerRuntime()
        config = DatabaseConfig.from_env()
        db = OracleDatabase(runtime=runtime, config=config, console=console)

        if not db.is_running():
            console.print("[yellow]Container is not running[/yellow]")
            return

        db.logs(follow=follow, tail=tail, since=since)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped following logs[/dim]")
    except Exception as e:
        console.print(f"[red]✗ Failed to get logs: {e}[/red]")
        raise click.Abort() from e


@database_group.command(name="status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed status")
def database_status(verbose: bool) -> None:
    """Check database container status."""
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import DatabaseConfig, OracleDatabase

    try:
        runtime = ContainerRuntime()
        config = DatabaseConfig.from_env()
        db = OracleDatabase(runtime=runtime, config=config, console=console)

        status_info = db.status()

        if status_info.exists:
            console.print(f"\n[bold]Container:[/bold] {config.container_name}")
            console.print(f"[bold]Running:[/bold] {'Yes' if status_info.running else 'No'}")
            console.print(f"[bold]Healthy:[/bold] {'Yes' if status_info.healthy else 'Unknown'}")

            if verbose:
                console.print(f"\n[bold]Image:[/bold] {status_info.image}")
                if status_info.created_at:
                    console.print(f"[bold]Created:[/bold] {status_info.created_at}")
                if status_info.uptime:
                    console.print(f"[bold]Uptime:[/bold] {status_info.uptime}")
                if status_info.ports:
                    console.print(f"[bold]Ports:[/bold] {status_info.ports}")
        else:
            console.print(f"[yellow]Container {config.container_name} does not exist[/yellow]")

    except Exception as e:
        console.print(f"[red]✗ Failed to get status: {e}[/red]")
        raise click.Abort() from e


# ============================================================================
# SQLCL COMMANDS (SQLcl Installation)
# ============================================================================


@cli.group(name="sqlcl")
def sqlcl_group() -> None:
    """Manage SQLcl installation.

    Install, verify, and manage Oracle SQLcl command-line tool.
    """


@sqlcl_group.command(name="install")
@click.option("--dir", "install_dir", type=click.Path(), help="Installation directory")
@click.option("--force", is_flag=True, help="Reinstall even if already installed")
def sqlcl_install(install_dir: str | None, force: bool) -> None:
    """Install Oracle SQLcl.

    Downloads and installs the latest version of SQLcl to ~/.local/bin by default.
    """
    from pathlib import Path

    from tools.oracle.sqlcl_installer import SQLclConfig, SQLclInstaller

    try:
        config = SQLclConfig()
        if install_dir:
            config.install_dir = Path(install_dir)

        installer = SQLclInstaller(config=config, console=console)

        console.print("[yellow]Installing SQLcl...[/yellow]")
        installed_path = installer.install(force=force)

        console.print(f"[green]✓ SQLcl installed to: {installed_path}[/green]")

        # Check if in PATH
        if not installer.is_in_path():
            console.print("\n[yellow]⚠ SQLcl is not in your PATH[/yellow]")
            instructions = installer.get_path_instructions()
            for instruction in instructions:
                console.print(f"  {instruction}")

    except Exception as e:
        console.print(f"[red]✗ Installation failed: {e}[/red]")
        raise click.Abort() from e


@sqlcl_group.command(name="verify")
def sqlcl_verify() -> None:
    """Verify SQLcl installation.

    Checks if SQLcl is installed and shows version information.
    """
    from tools.oracle.sqlcl_installer import SQLclInstaller

    try:
        installer = SQLclInstaller(console=console)

        if not installer.is_installed():
            console.print("[yellow]SQLcl is not installed[/yellow]")
            console.print("\nInstall with: uv run python tools/oracle_deploy.py sqlcl install")
            raise click.Abort()

        version = installer.get_version()
        in_path = installer.is_in_path()

        console.print("\n[green]✓ SQLcl is installed[/green]")
        console.print(f"  Version: {version}")
        console.print(f"  In PATH: {'Yes' if in_path else 'No'}")

        if not in_path:
            console.print("\n[yellow]To add SQLcl to PATH:[/yellow]")
            instructions = installer.get_path_instructions()
            for instruction in instructions:
                console.print(f"  {instruction}")

        # Test if it works
        if installer.verify():
            console.print("\n[green]✓ SQLcl is working correctly[/green]")
        else:
            console.print("\n[red]✗ SQLcl verification failed[/red]")
            raise click.Abort()

    except Exception as e:
        if not isinstance(e, click.Abort):
            console.print(f"[red]✗ Verification failed: {e}[/red]")
        raise click.Abort() from e


@sqlcl_group.command(name="uninstall")
@click.confirmation_option(prompt="Are you sure you want to uninstall SQLcl?")
def sqlcl_uninstall() -> None:
    """Uninstall SQLcl."""
    from tools.oracle.sqlcl_installer import SQLclInstaller

    try:
        installer = SQLclInstaller(console=console)

        if not installer.is_installed():
            console.print("[yellow]SQLcl is not installed[/yellow]")
            return

        console.print("[yellow]Uninstalling SQLcl...[/yellow]")
        installer.uninstall()
        console.print("[green]✓ SQLcl uninstalled[/green]")

    except Exception as e:
        console.print(f"[red]✗ Uninstall failed: {e}[/red]")
        raise click.Abort() from e


# ============================================================================
# WALLET COMMANDS (Autonomous Database Wallet Management)
# ============================================================================


@cli.group(name="wallet")
def wallet_group() -> None:
    """Manage Autonomous Database wallets.

    Extract, configure, and validate Oracle Autonomous Database wallet files.
    """


@wallet_group.command(name="extract")
@click.argument("wallet_zip", type=click.Path(exists=True))
@click.option("--dest", type=click.Path(), help="Destination directory (default: .envs/tns)")
def wallet_extract(wallet_zip: str, dest: str | None) -> None:
    """Extract wallet zip file.

    Extracts Wallet_*.zip file to specified directory.
    """
    from pathlib import Path

    from tools.oracle.wallet import WalletConfigurator

    configurator = WalletConfigurator()
    zip_path = Path(wallet_zip)
    dest_dir = Path(dest) if dest else None

    try:
        extracted_dir = configurator.extract_wallet(zip_path, dest_dir)
        console.print(f"[green]✓ Wallet extracted to: {extracted_dir}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to extract wallet: {e}[/red]")
        raise click.Abort() from e


@wallet_group.command(name="configure")
@click.option("--wallet-dir", type=click.Path(exists=True), help="Wallet directory")
@click.option("--non-interactive", is_flag=True, help="Skip interactive prompts")
def wallet_configure(wallet_dir: str | None, non_interactive: bool) -> None:
    """Interactive wallet configuration wizard.

    Guides through wallet setup and generates .env configuration.
    Replaces: app database configure
    """
    from pathlib import Path

    from tools.oracle.wallet import WalletConfigurator

    configurator = WalletConfigurator()
    wallet_path = Path(wallet_dir) if wallet_dir else None

    try:
        wallet_info = configurator.configure(wallet_path=wallet_path, interactive=not non_interactive)
        if wallet_info.is_valid:
            console.print("[green]✓ Wallet configuration complete![/green]")
    except Exception as e:
        console.print(f"[red]✗ Configuration failed: {e}[/red]")
        raise click.Abort() from e


@wallet_group.command(name="list-services")
@click.option("--wallet-dir", type=click.Path(exists=True), help="Wallet directory")
def wallet_list_services(wallet_dir: str | None) -> None:
    """List available database services in wallet.

    Shows all service names from tnsnames.ora.
    """
    from pathlib import Path

    from tools.oracle.wallet import WalletConfigurator

    configurator = WalletConfigurator()

    # Find wallet if not provided
    if wallet_dir:
        wallet_path = Path(wallet_dir)
    else:
        found = configurator.find_wallet()
        if not found:
            console.print("[yellow]⚠ No wallet found. Please specify --wallet-dir[/yellow]")
            raise click.Abort()
        wallet_path = found if found.is_dir() else configurator.extract_wallet(found)

    try:
        services = configurator.list_services(wallet_path, display=True)
        if not services:
            console.print("[yellow]No services found in wallet[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to list services: {e}[/red]")
        raise click.Abort() from e


@wallet_group.command(name="validate")
@click.option("--wallet-dir", type=click.Path(exists=True), help="Wallet directory")
def wallet_validate(wallet_dir: str | None) -> None:
    """Validate wallet files.

    Checks for required files and verifies wallet integrity.
    """
    from pathlib import Path

    from tools.oracle.wallet import WalletConfigurator

    configurator = WalletConfigurator()

    # Find wallet if not provided
    if wallet_dir:
        wallet_path = Path(wallet_dir)
    else:
        found = configurator.find_wallet()
        if not found:
            console.print("[yellow]⚠ No wallet found. Please specify --wallet-dir[/yellow]")
            raise click.Abort()
        wallet_path = found if found.is_dir() else configurator.extract_wallet(found)

    try:
        wallet_info = configurator.validate_wallet(wallet_path)

        if wallet_info.is_valid:
            console.print("[green]✓ Wallet is valid[/green]")
            console.print(f"\nWallet location: {wallet_info.wallet_dir}")
            console.print(f"Required files present: {wallet_info.required_files_present}")
            if wallet_info.services:
                console.print(f"Services found: {len(wallet_info.services)}")
        else:
            console.print("[red]✗ Wallet validation failed[/red]")
            for error in wallet_info.validation_errors or []:
                console.print(f"  • {error}")
            raise click.Abort()
    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        raise click.Abort() from e


# ============================================================================
# CONNECTION COMMANDS (Connection Testing)
# ============================================================================


@cli.group(name="connect")
def connect_group() -> None:
    """Test database connections.

    Test connectivity to Oracle databases in any deployment mode.
    """


@connect_group.command(name="test")
@click.option(
    "--mode",
    type=click.Choice(["managed", "external"]),
    help="Deployment mode (auto-detect if not specified)",
)
@click.option("--timeout", default=10, help="Connection timeout in seconds")
def connect_test(mode: str | None, timeout: int) -> None:
    """Test database connection.

    Attempts to connect and execute a simple query.
    Auto-detects wallet if configured.
    """
    from tools.oracle.connection import ConnectionConfig, ConnectionTester, DeploymentMode

    tester = ConnectionTester(console=console)

    try:
        # If mode specified, create config for that mode
        if mode:
            deployment_mode = DeploymentMode(mode.upper())
            config = ConnectionConfig.from_env()
            config.mode = deployment_mode
        else:
            # Auto-detect from environment
            config = ConnectionConfig.from_env()

        # Run connection test
        result = tester.test(config, timeout=timeout, display=True)

        if not result.success:
            raise click.Abort()

    except Exception as e:
        if not isinstance(e, click.Abort):
            console.print(f"[red]✗ Test failed: {e}[/red]")
        raise click.Abort() from e


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
        raise click.Abort() from e


# ============================================================================
# STATUS COMMAND (Overall Health Check)
# ============================================================================


@cli.command(name="status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed diagnostics")
@click.option(
    "--mode",
    type=click.Choice(["managed", "external"]),
    help="Check specific deployment mode",
)
def status(verbose: bool, mode: str | None) -> None:
    """Check overall system health.

    Comprehensive health check of all deployment components:
    - Container runtime (Docker/Podman)
    - Database container (if managed mode)
    - SQLcl installation
    - Wallet configuration (if wallet configured)
    - Database connectivity
    """
    from tools.oracle.connection import DeploymentMode
    from tools.oracle.health import HealthChecker

    checker = HealthChecker(console=console)

    try:
        # Convert mode string to enum if provided
        deployment_mode = DeploymentMode(mode.upper()) if mode else None

        # Run health checks
        health = checker.check_all(deployment_mode=deployment_mode, verbose=verbose)

        # Display results
        checker.display_health(health, verbose=verbose)

        # Exit with error code if unhealthy
        if not health.is_healthy:
            raise click.Abort()

    except Exception as e:
        if not isinstance(e, click.Abort):
            console.print(f"[red]✗ Health check failed: {e}[/red]")
        raise click.Abort() from e


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

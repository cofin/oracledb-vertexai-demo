# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Database container management CLI commands for Oracle AI Database 26ai (``adb-free`` and ``free``)."""

from __future__ import annotations

from pathlib import Path

import rich_click as click
from dotenv import load_dotenv
from rich.console import Console

from tools.oracle.container import ContainerNotFoundError, ContainerRuntime
from tools.oracle.database import ContainerFlavor, DatabaseConfig, OracleDatabase

__all__ = (
    "console",
    "database_group",
    "database_logs",
    "database_remove",
    "database_restart",
    "database_start",
    "database_status",
    "database_stop",
)

console = Console()


@click.group(name="database")
def database_group() -> None:
    """Manage the local Oracle AI Database 26ai container (managed mode).

    Deploys and manages ``adb-free:latest-26ai`` (with pre-installed APEX 26.1.5,
    ORDS 26.3 on HTTPS ``:8443``, and automated mTLS wallet export) or
    ``gvenzl/oracle-free`` when ``ORACLE_CONTAINER_FLAVOR=free``.
    """


@database_group.command(name="start")
@click.option("--pull", is_flag=True, help="Pull latest image before starting")
@click.option("--recreate", is_flag=True, help="Remove and recreate container if exists")
@click.option("--env-file", type=click.Path(exists=True), help="Environment file to load")
def database_start(pull: bool, recreate: bool, env_file: str | None) -> None:
    """Start the Oracle AI Database 26ai container and bootstrap wallet/schema readiness."""
    try:
        _database_start(pull=pull, recreate=recreate, env_file=env_file)
    except Exception as exc:
        console.print(f"[red]✗ Failed to start database: {exc}[/red]")
        raise click.Abort from exc


@database_group.command(name="stop")
@click.option("--timeout", default=30, help="Seconds to wait before forcing stop")
def database_stop(timeout: int) -> None:
    """Stop the Oracle database container."""
    try:
        _database_stop(timeout=timeout)
    except Exception as exc:
        console.print(f"[red]✗ Failed to stop database: {exc}[/red]")
        raise click.Abort from exc


@database_group.command(name="restart")
@click.option("--timeout", default=30, help="Seconds to wait for stop")
def database_restart(timeout: int) -> None:
    """Restart the Oracle database container."""
    try:
        _database_restart(timeout=timeout)
    except Exception as exc:
        console.print(f"[red]✗ Failed to restart database: {exc}[/red]")
        raise click.Abort from exc


@database_group.command(name="remove")
@click.option("--volumes", is_flag=True, help="Also remove associated volumes")
@click.option("--force", is_flag=True, help="Force removal even if running")
@click.confirmation_option(prompt="Are you sure you want to remove the container?")
def database_remove(volumes: bool, force: bool) -> None:
    """Remove the Oracle database container."""
    try:
        _database_remove(volumes=volumes, force=force)
    except ContainerNotFoundError:
        console.print("[yellow]Container already removed[/yellow]")
    except Exception as exc:
        console.print(f"[red]✗ Failed to remove database: {exc}[/red]")
        raise click.Abort from exc


@database_group.command(name="logs")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--tail", type=int, help="Number of lines to show from end")
@click.option("--since", help="Show logs since timestamp/duration")
def database_logs(follow: bool, tail: int | None, since: str | None) -> None:
    """View database container logs."""
    try:
        _database_logs(follow=follow, tail=tail, since=since)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped following logs[/dim]")
    except Exception as exc:
        console.print(f"[red]✗ Failed to get logs: {exc}[/red]")
        raise click.Abort from exc


@database_group.command(name="status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed status")
def database_status(verbose: bool) -> None:
    """Check database container, wallet, and APEX/ORDS endpoint status."""
    try:
        _database_status(verbose=verbose)
    except Exception as exc:
        console.print(f"[red]✗ Failed to get status: {exc}[/red]")
        raise click.Abort from exc


def _load_env_file(env_file: str | None) -> None:
    """Load an explicit env file, or the project ``.env`` when present."""
    env_path = Path(env_file or ".env")
    if not env_path.exists():
        return
    load_dotenv(env_path, override=True)


def _database() -> OracleDatabase:
    """Create the configured Oracle database manager."""
    runtime = ContainerRuntime()
    config = DatabaseConfig.from_env()
    return OracleDatabase(runtime=runtime, config=config, console=console)


def _print_adb_access_info(config: DatabaseConfig) -> None:
    """Print APEX Builder, Database Actions, wallet directory, and TNS service details."""
    ords_base = f"https://localhost:{config.https_port}/ords"
    console.print()
    console.print("[bold green]Autonomous AI Database Free 26ai Endpoints[/bold green]")
    console.print(f"  APEX Builder     : {ords_base}/apex")
    console.print(f"  Workspace        : {config.workspace_name} (user: {config.app_user.upper()})")
    console.print(f"  Database Actions : {ords_base}/sql-developer")
    console.print(f"  Wallet Directory : {config.wallet_dir}")
    console.print(f"  TNS Service      : {config.service_name}")


def _database_start(*, pull: bool, recreate: bool, env_file: str | None) -> None:
    """Start the Oracle container and display connection/APEX endpoints."""
    _load_env_file(env_file)
    db = _database()
    console.print("[yellow]Starting Oracle database container...[/yellow]")
    db.start(pull=pull, recreate=recreate)
    console.print("[green]✓ Database started successfully![/green]")
    if db.config.flavor == ContainerFlavor.ADB_FREE:
        _print_adb_access_info(db.config)


def _database_stop(*, timeout: int) -> None:
    """Stop the configured Oracle database container."""
    db = _database()
    if not db.is_running():
        console.print("[yellow]Container is not running[/yellow]")
        return
    console.print("[yellow]Stopping Oracle database container...[/yellow]")
    db.stop(timeout=timeout)
    console.print("[green]✓ Database stopped[/green]")


def _database_restart(*, timeout: int) -> None:
    """Restart the configured Oracle database container."""
    db = _database()
    console.print("[yellow]Restarting Oracle database container...[/yellow]")
    db.restart(timeout=timeout)
    console.print("[green]✓ Database restarted[/green]")


def _database_remove(*, volumes: bool, force: bool) -> None:
    """Remove the configured Oracle database container and optional volume."""
    db = _database()
    console.print("[yellow]Removing Oracle database container...[/yellow]")
    db.remove(volumes=volumes, force=force)
    console.print("[green]✓ Database container removed[/green]")


def _database_logs(*, follow: bool, tail: int | None, since: str | None) -> None:
    """Stream logs for the configured Oracle database container."""
    db = _database()
    if not db.is_running():
        console.print("[yellow]Container is not running[/yellow]")
        return
    db.logs(follow=follow, tail=tail, since=since)


def _database_status(*, verbose: bool) -> None:
    """Print container, wallet, service, and APEX/ORDS status for the configured flavor."""
    db = _database()
    status_info = db.status()
    config = db.config
    if not status_info.exists:
        console.print(f"[yellow]Container {config.container_name} does not exist[/yellow]")
        return

    healthy_label = "Yes" if status_info.healthy else ("No" if status_info.healthy is False else "Unknown")
    console.print(f"\n[bold]Container:[/bold] {config.container_name}")
    console.print(f"[bold]Flavor:[/bold] {config.flavor.value}")
    console.print(f"[bold]Running:[/bold] {'Yes' if status_info.running else 'No'}")
    console.print(f"[bold]Healthy:[/bold] {healthy_label}")

    if config.flavor == ContainerFlavor.ADB_FREE:
        wallet_exported = (config.wallet_dir / "tnsnames.ora").is_file()
        service_state = (
            "ready" if status_info.running and wallet_exported else ("running" if status_info.running else "stopped")
        )
        wallet_state = "exported" if wallet_exported else "pending"
        ords_base = f"https://localhost:{config.https_port}/ords"
        console.print(f"[bold]Service:[/bold] {config.service_name} ({service_state})")
        console.print(f"[bold]Wallet Directory:[/bold] {config.wallet_dir} ({wallet_state})")
        console.print(
            f"[bold]APEX Builder:[/bold] {ords_base}/apex (workspace: {config.workspace_name}, user: {config.app_user.upper()})"
        )
        console.print(f"[bold]Database Actions:[/bold] {ords_base}/sql-developer")
    else:
        console.print(f"[bold]Service:[/bold] {config.service_name}")

    if not verbose:
        return

    console.print(f"\n[bold]Image:[/bold] {status_info.image}")
    if status_info.created_at:
        console.print(f"[bold]Created:[/bold] {status_info.created_at}")
    if status_info.uptime:
        console.print(f"[bold]Uptime:[/bold] {status_info.uptime}")
    if status_info.ports:
        console.print(f"[bold]Ports:[/bold] {status_info.ports}")

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Database container management CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from rich.console import Console

if TYPE_CHECKING:
    from tools.oracle.apex_install import ApexInstaller
    from tools.oracle.database import OracleDatabase
    from tools.oracle.ords import OrdsSidecar

console = Console()


def _build_apex_installer(db: OracleDatabase) -> ApexInstaller:
    """Build an APEX installer bound to the running database container."""
    from tools.oracle.apex_install import ApexInstallConfig, ApexInstaller
    from tools.oracle.apex_media import ApexMedia, ApexMediaConfig

    media = ApexMedia(ApexMediaConfig.from_env())
    return ApexInstaller(db.runtime, db, media, ApexInstallConfig.from_env(), console=console)


def _auto_install_apex(db: OracleDatabase) -> None:
    """Install APEX after the DB is healthy when none is present (idempotent)."""
    installer = _build_apex_installer(db)
    if installer.installed_version() is None:
        console.print("[cyan]APEX not detected — installing (first run can take a few minutes)...[/cyan]")
        installer.install()
    else:
        console.print("[dim]APEX already present; skipping auto-install.[/dim]")


def _build_ords_sidecar(db: OracleDatabase) -> OrdsSidecar:
    """Build an ORDS sidecar serving the configured APEX images."""
    from tools.oracle.apex_media import ApexMedia, ApexMediaConfig
    from tools.oracle.ords import build_ords_sidecar

    media = ApexMedia(ApexMediaConfig.from_env())
    return build_ords_sidecar(db.runtime, media, console=console)


def _start_ords(db: OracleDatabase) -> None:
    """Start the ORDS sidecar (idempotent) so APEX has an HTTP front end."""
    _build_ords_sidecar(db).start()


def _load_env_file(env_file: str | None) -> None:
    """Load an explicit env file, or the project .env when present."""
    env_path = Path(env_file or ".env")
    if not env_path.exists():
        return

    from dotenv import load_dotenv

    load_dotenv(env_path, override=True)


def _database() -> OracleDatabase:
    """Create the configured Oracle database manager."""
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import DatabaseConfig, OracleDatabase

    runtime = ContainerRuntime()
    config = DatabaseConfig.from_env()
    return OracleDatabase(runtime=runtime, config=config, console=console)


@click.group(name="database")
def database_group() -> None:
    """Manage Oracle database container (managed mode).

    Commands for deploying and managing the Oracle 26ai demo container.
    Requires Docker or Podman to be installed.
    """


@database_group.command(name="start")
@click.option("--pull", is_flag=True, help="Pull latest image before starting")
@click.option("--recreate", is_flag=True, help="Remove and recreate container if exists")
@click.option("--env-file", type=click.Path(exists=True), help="Environment file to load")
@click.option("--skip-apex", is_flag=True, help="Do not auto-install APEX after the DB is healthy")
@click.option("--skip-ords", is_flag=True, help="Do not start the ORDS sidecar after APEX")
def database_start(pull: bool, recreate: bool, env_file: str | None, skip_apex: bool, skip_ords: bool) -> None:
    """Start Oracle database container.

    Deploys the Oracle Database Free container with local demo configuration,
    auto-installs APEX when missing (--skip-apex to opt out), then starts the
    ORDS sidecar for the APEX HTTP front end (--skip-ords to opt out).
    """
    try:
        _database_start(
            pull=pull, recreate=recreate, env_file=env_file, skip_apex=skip_apex, skip_ords=skip_ords
        )
    except Exception as e:
        console.print(f"[red]✗ Failed to start database: {e}[/red]")
        raise click.Abort from e


def _database_start(
    *, pull: bool, recreate: bool, env_file: str | None, skip_apex: bool = False, skip_ords: bool = False
) -> None:
    """Start the Oracle database and (unless skipped) ensure APEX + ORDS."""
    _load_env_file(env_file)
    db = _database()
    console.print("[yellow]Starting Oracle database container...[/yellow]")
    db.start(pull=pull, recreate=recreate)
    if not skip_apex:
        _auto_install_apex(db)
    if not skip_ords:
        _start_ords(db)
    console.print("[green]✓ Database started successfully![/green]")


@database_group.command(name="stop")
@click.option("--timeout", default=30, help="Seconds to wait before forcing stop")
def database_stop(timeout: int) -> None:
    """Stop Oracle database container."""
    try:
        _database_stop(timeout=timeout)
    except Exception as e:
        console.print(f"[red]✗ Failed to stop database: {e}[/red]")
        raise click.Abort from e


def _database_stop(*, timeout: int) -> None:
    """Stop the configured Oracle database (and the ORDS sidecar)."""
    db = _database()
    _build_ords_sidecar(db).stop(timeout=timeout)
    if not db.is_running():
        console.print("[yellow]Container is not running[/yellow]")
        return
    console.print("[yellow]Stopping Oracle database container...[/yellow]")
    db.stop(timeout=timeout)
    console.print("[green]✓ Database stopped[/green]")


@database_group.command(name="restart")
@click.option("--timeout", default=30, help="Seconds to wait for stop")
def database_restart(timeout: int) -> None:
    """Restart Oracle database container."""
    try:
        _database_restart(timeout=timeout)
    except Exception as e:
        console.print(f"[red]✗ Failed to restart database: {e}[/red]")
        raise click.Abort from e


def _database_restart(*, timeout: int) -> None:
    """Restart the configured Oracle database."""
    db = _database()
    console.print("[yellow]Restarting Oracle database container...[/yellow]")
    db.restart(timeout=timeout)
    console.print("[green]✓ Database restarted[/green]")


@database_group.command(name="remove")
@click.option("--volumes", is_flag=True, help="Also remove associated volumes")
@click.option("--force", is_flag=True, help="Force removal even if running")
@click.confirmation_option(prompt="Are you sure you want to remove the container?")
def database_remove(volumes: bool, force: bool) -> None:
    """Remove Oracle database container."""
    from tools.oracle.container import ContainerNotFoundError

    try:
        _database_remove(volumes=volumes, force=force)
    except ContainerNotFoundError:
        console.print("[yellow]Container already removed[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to remove database: {e}[/red]")
        raise click.Abort from e


def _database_remove(*, volumes: bool, force: bool) -> None:
    """Remove the configured Oracle database (and the ORDS sidecar)."""
    db = _database()
    _build_ords_sidecar(db).remove(force=force)
    console.print("[yellow]Removing Oracle database container...[/yellow]")
    db.remove(volumes=volumes, force=force)
    console.print("[green]✓ Database container removed[/green]")


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
    except Exception as e:
        console.print(f"[red]✗ Failed to get logs: {e}[/red]")
        raise click.Abort from e


def _database_logs(*, follow: bool, tail: int | None, since: str | None) -> None:
    """Print logs for the configured Oracle database."""
    db = _database()
    if not db.is_running():
        console.print("[yellow]Container is not running[/yellow]")
        return
    db.logs(follow=follow, tail=tail, since=since)


@database_group.command(name="status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed status")
def database_status(verbose: bool) -> None:
    """Check database container status."""
    try:
        _database_status(verbose=verbose)
    except Exception as e:
        console.print(f"[red]✗ Failed to get status: {e}[/red]")
        raise click.Abort from e


def _database_status(*, verbose: bool) -> None:
    """Print status for the configured Oracle database."""
    db = _database()
    status_info = db.status()
    config = db.config
    if not status_info.exists:
        console.print(f"[yellow]Container {config.container_name} does not exist[/yellow]")
        return
    console.print(f"\n[bold]Container:[/bold] {config.container_name}")
    console.print(f"[bold]Running:[/bold] {'Yes' if status_info.running else 'No'}")
    console.print(f"[bold]Healthy:[/bold] {'Yes' if status_info.healthy else 'Unknown'}")
    if not verbose:
        return
    console.print(f"\n[bold]Image:[/bold] {status_info.image}")
    if status_info.created_at:
        console.print(f"[bold]Created:[/bold] {status_info.created_at}")
    if status_info.uptime:
        console.print(f"[bold]Uptime:[/bold] {status_info.uptime}")
    if status_info.ports:
        console.print(f"[bold]Ports:[/bold] {status_info.ports}")

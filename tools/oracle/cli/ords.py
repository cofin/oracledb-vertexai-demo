# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Standalone ORDS lifecycle CLI commands (``manage.py infra ords``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import rich_click as click
from rich.console import Console

if TYPE_CHECKING:
    from tools.oracle.ords import OrdsSidecar

console = Console()


def _apex_media_status() -> tuple[str, str]:
    """Return APEX media and patch-state summary for standalone ORDS status."""
    from tools.oracle.cli.database import _apex_media_status as database_apex_media_status

    return database_apex_media_status()


def _build_ords_sidecar() -> OrdsSidecar:
    """Build the shared ORDS sidecar used by DB and standalone lifecycle commands."""
    from tools.oracle.apex_media import ApexMedia, ApexMediaConfig
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.ords import build_ords_sidecar

    runtime = ContainerRuntime()
    media = ApexMedia(ApexMediaConfig.from_env())
    return build_ords_sidecar(runtime, media, console=console)


def _print_status(status: dict[str, str]) -> None:
    """Print ORDS container and version-policy details."""
    console.print(f"[bold]Container:[/bold] {status.get('name', 'oracle-ords')}")
    console.print(f"[bold]Status:[/bold] {status.get('status', 'unknown')}")
    if image := status.get("image"):
        console.print(f"[bold]Image:[/bold] {image}")
    if ports := status.get("ports"):
        console.print(f"[bold]Ports:[/bold] {ports}")
    console.print(f"[bold]ORDS Version:[/bold] {status.get('ords_version', 'unknown')}")
    console.print(f"[bold]Minimum ORDS:[/bold] {status.get('minimum_version', '26.1.1')}")
    console.print(f"[bold]Preferred ORDS:[/bold] {status.get('preferred_version', '26.1.2')}")
    console.print(f"[bold]Version Status:[/bold] {status.get('version_status', 'unknown')}")


def _print_readiness(sidecar: OrdsSidecar) -> None:
    """Print ORDS HTTP readiness probe results."""
    console.print(f"[bold]/ords/ HTTP:[/bold] {'ready' if sidecar.http_ready('/ords/') else 'not ready'}")
    console.print(f"[bold]/i/ HTTP:[/bold] {'ready' if sidecar.http_ready('/i/') else 'not ready'}")


def _print_apex_status() -> None:
    """Print APEX media and patch-state details for ORDS status."""
    media, patch_state = _apex_media_status()
    console.print(f"[bold]APEX Media:[/bold] {media}")
    console.print(f"[bold]APEX Patch:[/bold] {patch_state}")


def _ords_status() -> None:
    """Print standalone ORDS status details."""
    sidecar = _build_ords_sidecar()
    status = sidecar.status()
    if status is None:
        console.print("[yellow]Container oracle-ords does not exist[/yellow]")
        return
    _print_status(status)
    _print_readiness(sidecar)
    _print_apex_status()


@click.group(name="ords")
def ords_group() -> None:
    """Manage the optional ORDS sidecar independently from the database."""


@ords_group.command(name="start")
@click.option("--recreate", is_flag=True, help="Remove and recreate the ORDS sidecar if it exists")
def ords_start(recreate: bool) -> None:
    """Start the ORDS sidecar."""
    try:
        _build_ords_sidecar().start(recreate=recreate)
    except Exception as e:
        console.print(f"[red]Failed to start ORDS: {e}[/red]")
        raise click.Abort from e


@ords_group.command(name="stop")
@click.option("--timeout", default=30, help="Seconds to wait before forcing stop")
def ords_stop(timeout: int) -> None:
    """Stop the ORDS sidecar."""
    try:
        _build_ords_sidecar().stop(timeout=timeout)
        console.print("[green]ORDS sidecar stopped[/green]")
    except Exception as e:
        console.print(f"[red]Failed to stop ORDS: {e}[/red]")
        raise click.Abort from e


@ords_group.command(name="restart")
@click.option("--timeout", default=30, help="Seconds to wait before forcing stop")
def ords_restart(timeout: int) -> None:
    """Restart the ORDS sidecar."""
    try:
        sidecar = _build_ords_sidecar()
        sidecar.stop(timeout=timeout)
        sidecar.start(recreate=True)
    except Exception as e:
        console.print(f"[red]Failed to restart ORDS: {e}[/red]")
        raise click.Abort from e


@ords_group.command(name="status")
def ords_status() -> None:
    """Report ORDS runtime, version policy, and HTTP readiness."""
    try:
        _ords_status()
    except Exception as e:
        console.print(f"[red]Failed to read ORDS status: {e}[/red]")
        raise click.Abort from e


@ords_group.command(name="logs")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--tail", type=int, help="Number of lines to show from end")
def ords_logs(follow: bool, tail: int | None) -> None:
    """View ORDS sidecar logs."""
    try:
        _build_ords_sidecar().logs(follow=follow, tail=tail)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped following logs[/dim]")
    except Exception as e:
        console.print(f"[red]Failed to get ORDS logs: {e}[/red]")
        raise click.Abort from e


@ords_group.command(name="remove")
@click.option("--force", is_flag=True, help="Force removal even if running")
def ords_remove(force: bool) -> None:
    """Remove the ORDS sidecar container."""
    try:
        _build_ords_sidecar().remove(force=force)
        console.print("[green]ORDS sidecar removed[/green]")
    except Exception as e:
        console.print(f"[red]Failed to remove ORDS: {e}[/red]")
        raise click.Abort from e

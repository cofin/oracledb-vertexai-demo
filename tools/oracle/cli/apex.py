# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""APEX install/upgrade/status CLI commands (``manage.py infra apex``)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import rich_click as click
from rich.console import Console

if TYPE_CHECKING:
    from tools.oracle.apex_install import ApexInstaller

console = Console()


def _build_installer(*, apex_version: str | None = None, english: bool | None = None) -> ApexInstaller:
    """Build an APEX installer for the configured container and media version."""
    from tools.oracle.apex_install import ApexInstallConfig, ApexInstaller
    from tools.oracle.apex_media import ApexMedia, ApexMediaConfig
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import DatabaseConfig, OracleDatabase

    media_config = ApexMediaConfig.from_env()
    if apex_version is not None:
        media_config = replace(media_config, version=apex_version)
    if english is not None:
        media_config = replace(media_config, english_only=english)

    runtime = ContainerRuntime()
    db = OracleDatabase(runtime=runtime, config=DatabaseConfig.from_env(), console=console)
    media = ApexMedia(media_config)
    return ApexInstaller(runtime, db, media, ApexInstallConfig.from_env(), console=console)


@click.group(name="apex")
def apex_group() -> None:
    """Install, upgrade, and inspect Oracle APEX in the local container."""


@apex_group.command(name="install")
@click.option("--apex-version", default=None, help="APEX version to install (default 26.1 / env)")
@click.option("--force", is_flag=True, help="Re-run install even when already at target")
@click.option("--english/--full", default=True, help="Use the English-only zip (default) or the full zip")
def apex_install(apex_version: str | None, force: bool, english: bool) -> None:
    """Install APEX into the container PDB (idempotent)."""
    try:
        installer = _build_installer(apex_version=apex_version, english=english)
        version = installer.install(force=force)
        console.print(f"[green]✓ APEX {version} installed.[/green]")
    except Exception as e:
        console.print(f"[red]✗ APEX install failed: {e}[/red]")
        raise click.Abort from e


@apex_group.command(name="upgrade")
@click.option("--apex-version", default=None, help="Target APEX version to upgrade to")
def apex_upgrade(apex_version: str | None) -> None:
    """Upgrade APEX in place to a newer version (idempotent re-run)."""
    try:
        installer = _build_installer(apex_version=apex_version)
        version = installer.install()
        console.print(f"[green]✓ APEX upgraded to {version}.[/green]")
    except Exception as e:
        console.print(f"[red]✗ APEX upgrade failed: {e}[/red]")
        raise click.Abort from e


@apex_group.command(name="status")
def apex_status() -> None:
    """Report the installed APEX version against the configured target."""
    try:
        installer = _build_installer()
        installed = installer.installed_version() or "not installed"
        target = installer.media.config.version
        console.print(f"[bold]APEX installed:[/bold] {installed}\n[bold]Target:[/bold] {target}")
    except Exception as e:
        console.print(f"[red]✗ Failed to read APEX status: {e}[/red]")
        raise click.Abort from e

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""APEX install/upgrade/status CLI commands (``manage.py infra apex``)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from rich.console import Console

if TYPE_CHECKING:
    from tools.oracle.apex_install import ApexInstaller
    from tools.oracle.apex_lang import ApexLang

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


def _build_apex_lang() -> ApexLang:
    """Build the SQLcl-backed APEXlang workflow wrapper."""
    from tools.oracle.apex_lang import ApexLang, ApexLangConfig
    from tools.oracle.sqlcl_installer import SQLclInstaller

    return ApexLang(
        installer=SQLclInstaller(console=console),
        config=ApexLangConfig.from_env(),
        console=console,
    )


@click.group(name="apex")
def apex_group() -> None:
    """Install, upgrade, inspect, and source-control Oracle APEX."""


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


@apex_group.command(name="generate")
@click.option("--alias", "app_alias", default="cymbal-coffee-ops", show_default=True, help="APEX app alias")
@click.option("--app-name", default=None, help="Starter application display name")
@click.option("--app-id", type=int, default=None, help="Starter application ID")
@click.option("--workspace", default=None, help="APEX workspace name")
@click.option("--schema", default=None, help="Parsing schema")
@click.option("--force", is_flag=True, help="Remove and recreate existing generated files")
def apex_generate(
    app_alias: str,
    app_name: str | None,
    app_id: int | None,
    workspace: str | None,
    schema: str | None,
    force: bool,
) -> None:
    """Generate starter APEXlang source files with SQLcl 26.1.2+."""
    try:
        result = _build_apex_lang().generate(
            alias=app_alias,
            app_name=app_name,
            app_id=app_id,
            workspace=workspace,
            schema=schema,
            force=force,
        )
        console.print(f"[green]✓ Generated APEXlang source at {result.target_path}[/green]")
    except Exception as e:
        console.print(f"[red]✗ APEXlang generate failed: {e}[/red]")
        raise click.Abort from e


@apex_group.command(name="export")
@click.option("--app-id", type=int, required=True, help="APEX application ID to export")
@click.option("--alias", "app_alias", default="cymbal-coffee-ops", show_default=True, help="APEX app alias")
@click.option("--clean/--no-clean", default=True, show_default=True, help="Use SQLcl -force for stable output")
def apex_export(app_id: int, app_alias: str, clean: bool) -> None:
    """Export an existing APEX app as APEXlang source with SQLcl 26.1.2+."""
    try:
        result = _build_apex_lang().export(app_id=app_id, alias=app_alias, clean=clean)
        console.print(f"[green]✓ Exported APEXlang source to {result.target_path}[/green]")
    except Exception as e:
        console.print(f"[red]✗ APEXlang export failed: {e}[/red]")
        raise click.Abort from e


@apex_group.command(name="validate")
@click.option("--alias", "app_alias", default="cymbal-coffee-ops", show_default=True, help="APEX app alias")
@click.option("--input", "input_path", type=click.Path(), default=None, help="APEXlang input path")
@click.option("--workspace", default=None, help="APEX workspace name")
@click.option("--deployment", default=None, help="Deployment file name or path")
@click.option("--debug", is_flag=True, help="Enable SQLcl APEX validation debug output")
def apex_validate(
    app_alias: str,
    input_path: str | None,
    workspace: str | None,
    deployment: str | None,
    debug: bool,
) -> None:
    """Validate APEXlang source with SQLcl 26.1.2+."""
    try:
        result = _build_apex_lang().validate(
            alias=app_alias,
            input_path=Path(input_path) if input_path else None,
            workspace=workspace,
            deployment=deployment,
            debug=debug,
        )
        console.print(f"[green]✓ Validated APEXlang source at {result.target_path}[/green]")
    except Exception as e:
        console.print(f"[red]✗ APEXlang validation failed: {e}[/red]")
        raise click.Abort from e


@apex_group.command(name="import")
@click.option("--alias", "app_alias", default="cymbal-coffee-ops", show_default=True, help="APEX app alias")
@click.option("--input", "input_path", type=click.Path(), default=None, help="APEXlang input path")
@click.option("--workspace", default=None, help="APEX workspace name")
@click.option("--schema", default=None, help="Parsing schema")
@click.option("--app-id", type=int, default=None, help="Application ID override")
@click.option("--app-name", default=None, help="Application name override")
@click.option("--deployment", default=None, help="Deployment file name or path")
@click.option("--debug", is_flag=True, help="Enable SQLcl APEX import debug output")
def apex_import(
    app_alias: str,
    input_path: str | None,
    workspace: str | None,
    schema: str | None,
    app_id: int | None,
    app_name: str | None,
    deployment: str | None,
    debug: bool,
) -> None:
    """Import APEXlang source into APEX with SQLcl 26.1.2+."""
    try:
        result = _build_apex_lang().import_app(
            alias=app_alias,
            input_path=Path(input_path) if input_path else None,
            workspace=workspace,
            schema=schema,
            app_id=app_id,
            app_name=app_name,
            deployment=deployment,
            debug=debug,
        )
        console.print(f"[green]✓ Imported APEXlang source from {result.target_path}[/green]")
    except Exception as e:
        console.print(f"[red]✗ APEXlang import failed: {e}[/red]")
        raise click.Abort from e

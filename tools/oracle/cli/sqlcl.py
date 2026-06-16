# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""SQLcl installation and management CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from rich.console import Console

if TYPE_CHECKING:
    from tools.oracle.sqlcl_installer import SQLclConfig, SQLclInstaller

console = Console()


@click.group(name="sqlcl")
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
    from tools.oracle.sqlcl_installer import SQLclConfig, SQLclInstaller

    try:
        config = SQLclConfig()
        if install_dir:
            config.install_dir = Path(install_dir)
        install_sqlcl(config=config, installer_type=SQLclInstaller, force=force)
    except Exception as e:
        console.print(f"[red]✗ Installation failed: {e}[/red]")
        raise click.Abort from e


def install_sqlcl(*, config: SQLclConfig, installer_type: type[SQLclInstaller], force: bool) -> None:
    """Install SQLcl and print PATH guidance."""
    installer = installer_type(config=config, console=console)
    console.print("[yellow]Installing SQLcl...[/yellow]")
    installed_path = installer.install(force=force)
    console.print(f"[green]✓ SQLcl installed to: {installed_path}[/green]")
    print_path_guidance(installer)


def print_path_guidance(installer: SQLclInstaller) -> None:
    """Print PATH guidance when SQLcl is outside PATH."""
    if installer.is_in_path():
        return
    console.print("\n[yellow]⚠ SQLcl is not in your PATH[/yellow]")
    for instruction in installer.get_path_instructions():
        console.print(f"  {instruction}")


@sqlcl_group.command(name="verify")
def sqlcl_verify() -> None:
    """Verify SQLcl installation.

    Checks if SQLcl is installed and shows version information.
    """
    from tools.oracle.sqlcl_installer import SQLclInstaller

    try:
        verify_sqlcl(SQLclInstaller(console=console))
    except Exception as e:
        if not isinstance(e, click.Abort):
            console.print(f"[red]✗ Verification failed: {e}[/red]")
        raise click.Abort from e


def verify_sqlcl(installer: SQLclInstaller) -> None:
    """Verify SQLcl installation and print status."""
    if not installer.is_installed():
        console.print("[yellow]SQLcl is not installed[/yellow]")
        console.print("\nInstall with: uv run python manage.py install sqlcl")
        raise click.Abort
    version = installer.get_version()
    in_path = installer.is_in_path()
    console.print("\n[green]✓ SQLcl is installed[/green]")
    console.print(f"  Version: {version}")
    console.print(f"  In PATH: {'Yes' if in_path else 'No'}")
    print_path_guidance(installer)
    if installer.verify():
        console.print("\n[green]✓ SQLcl is working correctly[/green]")
        return
    console.print("\n[red]✗ SQLcl verification failed[/red]")
    raise click.Abort


@sqlcl_group.command(name="uninstall")
@click.confirmation_option(prompt="Are you sure you want to uninstall SQLcl?")
def sqlcl_uninstall() -> None:
    """Uninstall SQLcl."""
    from tools.oracle.sqlcl_installer import SQLclInstaller

    try:
        uninstall_sqlcl(SQLclInstaller(console=console))
    except Exception as e:
        console.print(f"[red]✗ Uninstall failed: {e}[/red]")
        raise click.Abort from e


def uninstall_sqlcl(installer: SQLclInstaller) -> None:
    """Uninstall SQLcl if present."""
    if not installer.is_installed():
        console.print("[yellow]SQLcl is not installed[/yellow]")
        return
    console.print("[yellow]Uninstalling SQLcl...[/yellow]")
    installer.uninstall()
    console.print("[green]✓ SQLcl uninstalled[/green]")

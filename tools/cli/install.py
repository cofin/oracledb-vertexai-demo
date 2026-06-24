# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Installation commands for external prerequisites."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from tools.lib.utils import (
    AntigravityMCPConfigTarget,
    build_antigravity_mcp_config,
    detect_deployment_mode,
    get_antigravity_mcp_config_path,
    is_tool_installed,
    run_command,
    write_antigravity_mcp_config,
)

if TYPE_CHECKING:
    from tools.oracle.sqlcl_installer import SQLclConfig, SQLclInstaller

console = Console()


@click.group(name="install")
def install_group() -> None:
    """Install external tool prerequisites.

    Manages installation of:
    - SQLcl: Oracle's SQL command-line tool
    """


@install_group.command(name="all")
@click.option(
    "--mode",
    type=click.Choice(["managed", "external"], case_sensitive=False),
    help="Install prerequisites for specific mode (auto-detect if not specified)",
)
@click.option("--force", is_flag=True, help="Force reinstall even if already installed")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
def install_all_command(mode: str | None, force: bool, yes: bool) -> None:
    """Install all prerequisites for deployment mode.

    Idempotent: Safe to run multiple times. Skips if already installed unless --force is used.

    Prerequisites:
    - SQLcl: Oracle's SQL command-line tool
    - Docker/Podman: (checked, not auto-installed)

    Note: Base tools like 'uv' and 'bun' should be installed via the Makefile.
    """
    if mode is None:
        mode = detect_deployment_mode()

    console.rule(f"[bold blue]Installing Prerequisites for '{mode}' Mode", style="blue")
    console.print()

    if not yes and not Confirm.ask("Proceed with installation?", default=True):
        console.print("[yellow]Installation cancelled[/yellow]")
        return

    # Install SQLcl
    ctx = click.get_current_context()
    if ctx:
        ctx.invoke(install_sqlcl_command, force=force)

    # For managed mode, check Docker/Podman
    if mode == "managed":
        console.print()
        console.print("[yellow]🐋 Checking for Docker/Podman...[/yellow]")

        has_docker = shutil.which("docker") is not None
        has_podman = shutil.which("podman") is not None

        if has_docker:
            console.print("[green]✓ Docker found[/green]")
        elif has_podman:
            console.print("[green]✓ Podman found[/green]")
        else:
            console.print("[red]✗ Neither Docker nor Podman found[/red]")
            console.print()
            console.print("[yellow]⚠ Managed mode requires Docker or Podman[/yellow]")
            console.print("[dim]Install from: https://www.docker.com/get-started[/dim]")

    console.print()
    console.print("[green]✓ Installation complete![/green]")


@install_group.command(name="list")
def install_list_command() -> None:
    """List available installation components."""
    console.rule("[bold blue]Available Installation Components", style="blue")
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan", width=15)
    table.add_column("Required", width=10)
    table.add_column("Modes", width=30)
    table.add_column("Description")

    table.add_row("java", "[yellow]Optional[/yellow]", "managed, external", "Java 11+ (required for SQLcl)")
    table.add_row("sqlcl", "[yellow]Optional[/yellow]", "managed, external", "Oracle SQL command-line tool")
    table.add_row("docker", "[yellow]Optional[/yellow]", "managed", "Container runtime (not auto-installed)")
    table.add_row(
        "mcp-toolbox",
        "[yellow]Optional[/yellow]",
        "managed, external",
        "Antigravity MCP config for SQLcl and MCP Toolbox Oracle",
    )

    console.print(table)
    console.print()
    console.print("[dim]Tip: Run 'python3 manage.py install <component>' to install[/dim]")
    console.print()


@install_group.command(name="sqlcl")
@click.option("--dir", "install_dir", type=click.Path(), help="Installation directory (default: ~/.local/bin)")
@click.option("--force", is_flag=True, help="Reinstall even if already installed")
@click.option(
    "--connection-name",
    default="cymbal_coffee",
    help="Retained for compatibility; Antigravity MCP config does not save credentials.",
)
def install_sqlcl_command(install_dir: str | None, force: bool, connection_name: str) -> None:
    """Install Oracle SQLcl command-line tool.

    Idempotent: Safe to run multiple times. Skips installation if SQLcl is already
    installed unless --force flag is used.

    Optional tool for advanced Oracle database operations.
    Requires Java 11 or higher to be installed.

    IMPORTANT: SQLcl requires Java 11+. Check with 'java -version'.
    """
    console.print("[yellow]📦 Checking SQLcl installation...[/yellow]")
    console.print()
    if connection_name != "cymbal_coffee":
        console.print(
            "[dim]Antigravity MCP config uses SQLcl directly and does not write saved connection names.[/dim]"
        )
        console.print()

    # Check for Java before proceeding
    java_path = shutil.which("java")
    if not java_path:
        console.print("[red]✗ Java not found![/red]")
        console.print()
        console.print("[bold]SQLcl requires Java 11 or higher.[/bold]")
        console.print()
        console.print("[yellow]Install Java on Ubuntu/Debian:[/yellow]")
        console.print("  [cyan]sudo apt update && sudo apt install -y default-jre[/cyan]")
        console.print()
        console.print("[yellow]Or install a specific version (Ubuntu/Debian):[/yellow]")
        console.print("  [cyan]sudo apt install openjdk-17-jre-headless[/cyan]  # Java 17 (recommended)")
        console.print("  [cyan]sudo apt install openjdk-21-jre-headless[/cyan]  # Java 21 (latest LTS)")
        console.print("  [cyan]sudo apt install openjdk-11-jre-headless[/cyan]  # Java 11 (minimum)")
        console.print()
        console.print("[yellow]RHEL/CentOS/Fedora (yum/dnf):[/yellow]")
        console.print("  [cyan]sudo yum install java-17-openjdk[/cyan]           # RHEL/CentOS 7-8")
        console.print("  [cyan]sudo dnf install java-17-openjdk[/cyan]           # RHEL/CentOS 9+, Fedora")
        console.print("  [cyan]sudo dnf install java-21-openjdk[/cyan]           # Latest LTS")
        console.print()
        console.print("[yellow]Other platforms:[/yellow]")
        console.print("  • macOS: [cyan]brew install openjdk@17[/cyan]")
        console.print("  • Download from: [dim]https://adoptium.net/[/dim]")
        console.print()
        console.print("[dim]After installing Java, run this command again.[/dim]")
        raise click.Abort

    # Check Java version
    returncode, _stdout, _ = run_command(["java", "-version"], check=False)
    if returncode == 0:
        console.print("[green]✓ Java found[/green]")
        console.print()

    # Check if already installed
    is_installed, version_str = is_tool_installed("sql", "-V")
    if is_installed and not force:
        console.print(f"[green]✓ SQLcl already installed: {version_str.split(chr(10))[0]}[/green]")
        sqlcl_path = shutil.which("sql")
        console.print(f"[dim]  Location: {sqlcl_path}[/dim]")
        console.print("[dim]  Use --force to reinstall[/dim]")
        print_antigravity_mcp_next_step()
        return

    # If force flag, show warning
    if is_installed and force:
        console.print("[yellow]⚠ Reinstalling SQLcl (--force flag used)[/yellow]")
        console.print()

    console.print("[yellow]📦 Installing Oracle SQLcl...[/yellow]")
    console.print()

    # Use SQLcl installer directly
    from tools.oracle.sqlcl_installer import SQLclConfig, SQLclInstaller

    try:
        config = SQLclConfig()
        if install_dir:
            config.install_dir = Path(install_dir)
        install_sqlcl_with_config(config, SQLclInstaller, force=force)
    except Exception as e:
        console.print(f"[red]✗ Installation failed: {e}[/red]")
        raise click.Abort from e

    # Post-installation instructions
    console.print()
    console.print("[bold]Test SQLcl:[/bold]")
    console.print("  [cyan]sql -V[/cyan]")
    console.print()
    console.print("[dim]Note: Make sure ~/.local/bin is in your PATH[/dim]")

    print_antigravity_mcp_next_step()


@install_group.command(name="mcp-toolbox")
@click.option("--dry-run", is_flag=True, help="Print MCP Toolbox and Oracle Skills guidance without writing config.")
@click.option(
    "--workspace", "workspace", is_flag=True, help="Write workspace Antigravity config to .agents/mcp_config.json."
)
@click.option(
    "--ide", "ide", is_flag=True, help="Write explicit IDE Antigravity config to ~/.gemini/config/mcp_config.json."
)
@click.option(
    "--cli-global",
    "cli_global",
    is_flag=True,
    help="Write explicit Antigravity CLI global config to ~/.gemini/antigravity-cli/mcp_config.json.",
)
def install_mcp_toolbox_command(*, dry_run: bool, workspace: bool, ide: bool, cli_global: bool) -> None:
    """Prepare Antigravity MCP config for MCP Toolbox Oracle.

    This command prints install guidance by default. Use --workspace, --ide, or
    --cli-global to write the selected Antigravity MCP config.
    """
    selected_count = int(workspace) + int(ide) + int(cli_global)
    if selected_count > 1:
        msg = "Choose only one of --workspace, --ide, or --cli-global."
        raise click.UsageError(msg)

    target: AntigravityMCPConfigTarget = "workspace"
    if ide:
        target = "ide"
    elif cli_global:
        target = "cli-global"
    config_path = get_antigravity_mcp_config_path(target)
    config = build_antigravity_mcp_config()

    console.rule("[bold blue]Antigravity MCP Toolbox Configuration", style="blue")
    console.print()

    toolbox_path = shutil.which("toolbox")
    if toolbox_path:
        console.print(f"[green]✓ MCP Toolbox found:[/green] [dim]{toolbox_path}[/dim]")
    else:
        console.print("[yellow]⚠ MCP Toolbox command not found on PATH[/yellow]")
        console.print("[dim]Install MCP Toolbox for Databases and ensure the 'toolbox' command is available.[/dim]")

    console.print()
    console.print("[bold]MCP Toolbox Oracle server command:[/bold]")
    console.print("  [cyan]toolbox --prebuilt oracledb --stdio[/cyan]")
    console.print()
    console.print("[bold]Environment placeholders expected by the config:[/bold]")
    console.print("  [cyan]ORACLE_CONNECTION_STRING[/cyan]")
    console.print("  [cyan]ORACLE_USERNAME[/cyan]")
    console.print("  [cyan]ORACLE_PASSWORD[/cyan]")
    console.print("  [cyan]ORACLE_WALLET[/cyan]")
    console.print("  [cyan]ORACLE_USE_OCI[/cyan]")
    console.print()
    console.print("[bold]Oracle Skills guidance:[/bold]")
    console.print("  [cyan]npx skills add oracle/skills/apex[/cyan]")
    console.print("  [cyan]npx skills add oracle/skills/db[/cyan]")
    console.print()
    console.print("[bold]Antigravity config target:[/bold]")
    console.print(f"  [cyan]{config_path}[/cyan]")
    console.print()
    console.print("[bold]Config preview:[/bold]")
    console.print_json(data=config)

    if dry_run or selected_count == 0:
        console.print()
        console.print("[yellow]Dry run only; no files were written.[/yellow]")
        console.print("[dim]Use --workspace to write .agents/mcp_config.json for this checkout.[/dim]")
        return

    try:
        written_path = write_antigravity_mcp_config(target)
    except Exception as e:
        msg = f"Failed to write Antigravity MCP config: {e}"
        raise click.ClickException(msg) from e

    console.print()
    console.print(f"[green]✓ Wrote Antigravity MCP config:[/green] [cyan]{written_path}[/cyan]")


def install_sqlcl_with_config(config: SQLclConfig, installer_type: type[SQLclInstaller], *, force: bool) -> None:
    """Install SQLcl with the configured installer class."""
    installer = installer_type(config=config, console=console)
    installed_path = installer.install(force=force)
    console.print(f"[green]✓ SQLcl installed to: {installed_path}[/green]")
    if installer.is_in_path():
        return
    console.print("\n[yellow]⚠ SQLcl is not in your PATH[/yellow]")
    for instruction in installer.get_path_instructions():
        console.print(f"  {instruction}")


def print_antigravity_mcp_next_step() -> None:
    """Print explicit Antigravity MCP config guidance without writing files."""
    console.print()
    console.print("[bold]Antigravity MCP config:[/bold]")
    console.print("  [cyan]python manage.py install mcp-toolbox --workspace[/cyan]")

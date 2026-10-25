# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Project initialization CLI command."""

from __future__ import annotations

import rich_click as click
from rich.console import Console
from rich.prompt import Confirm, Prompt

from tools.cli.doctor import doctor_command
from tools.cli.install import install_all_command
from tools.lib.utils import check_env_file, create_env_interactive, detect_deployment_mode
from tools.oracle.adb import ADB_FREE_CONTAINER_NAME, ADB_FREE_DEFAULT_IMAGE

__all__ = ("console", "init_command")

console = Console()


@click.command(name="init")
@click.option(
    "--mode",
    type=click.Choice(["managed", "external"], case_sensitive=False),
    help="Deployment mode (auto-detect if not specified)",
)
@click.option("--run-install", is_flag=True, help="Automatically run 'install all' after initialization")
@click.option("--run-doctor", is_flag=True, help="Automatically run 'doctor' after initialization")
@click.option("--non-interactive", is_flag=True, help="Skip interactive prompts (use defaults/env vars)")
def init_command(mode: str | None, run_install: bool, run_doctor: bool, non_interactive: bool) -> None:
    """Initialize project environment and ``.env`` configuration.

    Modes:
    - managed: Run Oracle Autonomous AI Database Free 26ai (``adb-free:latest-26ai``) in Docker/Podman
    - external: Connect to an existing Oracle 26ai database (standard or mTLS wallet)
    """
    console.rule("[bold blue]Project Initialization", style="blue", align="left")
    console.print()

    resolved_mode = _resolve_init_mode(mode, non_interactive=non_interactive)
    console.print()

    console.print("[yellow]📄 Configuring environment...[/yellow]")
    if not create_env_interactive(resolved_mode, non_interactive):
        console.print("[red]✗ Failed to configure .env file[/red]")
        raise click.Abort
    console.print()

    _print_mode_next_steps(resolved_mode)
    console.print()

    if run_install:
        console.rule("[bold yellow]Running Installation", style="yellow")
        console.print()
        ctx = click.get_current_context()
        if ctx:
            ctx.invoke(install_all_command, mode=resolved_mode, force=False, yes=non_interactive)

    if run_doctor:
        console.rule("[bold yellow]Running Health Check", style="yellow")
        console.print()
        ctx = click.get_current_context()
        if ctx:
            ctx.invoke(doctor_command, mode=resolved_mode, json_output=False, verbose=False)

    _print_completion_footer(run_install=run_install, run_doctor=run_doctor)


def _resolve_init_mode(mode: str | None, *, non_interactive: bool) -> str:
    """Determine deployment mode from CLI flag, existing ``.env``, or interactive prompt."""
    if mode is not None:
        console.print(f"[cyan]📌 Using specified mode: [bold]{mode}[/bold][/cyan]")
        return mode

    has_env = check_env_file()
    if has_env:
        detected = detect_deployment_mode()
        console.print(f"[cyan]🔍 Auto-detected mode from .env: [bold]{detected}[/bold][/cyan]")
        if not non_interactive and Confirm.ask("Change deployment mode?", default=False):
            return Prompt.ask("Select mode", choices=["managed", "external"], default=detected)
        return detected

    console.print("[yellow]📄 No .env file found[/yellow]")
    if non_interactive:
        console.print("[cyan]Using default mode: [bold]managed[/bold][/cyan]")
        return "managed"
    return Prompt.ask("Select deployment mode", choices=["managed", "external"], default="managed")


def _print_mode_next_steps(mode: str) -> None:
    """Print mode-specific follow-up commands after ``.env`` creation."""
    console.print(f"[bold]Next steps for [cyan]{mode}[/cyan] mode:[/bold]")
    console.print()
    if mode == "managed":
        console.print("  1. Run: [cyan]make install[/cyan]")
        console.print(
            f"  2. Run: [cyan]make start-infra[/cyan] "
            f"[dim](starts {ADB_FREE_CONTAINER_NAME} from {ADB_FREE_DEFAULT_IMAGE} and exports .envs/tns)[/dim]"
        )
        console.print("  3. Run: [cyan]uv run coffee upgrade[/cyan]")
        console.print("  4. Run: [cyan]uv run coffee run[/cyan] [dim](APEX at https://localhost:8443/ords/apex)[/dim]")
        return

    console.print(
        "  1. (If using wallet) Run: [cyan]uv run python manage.py database wallet extract Wallet_*.zip[/cyan]"
    )
    console.print("  2. Run: [cyan]uv run python manage.py database connect test[/cyan]")
    console.print("  3. Run: [cyan]uv run coffee upgrade[/cyan]")
    console.print("  4. Run: [cyan]uv run coffee run[/cyan]")


def _print_completion_footer(*, run_install: bool, run_doctor: bool) -> None:
    """Print the final initialization summary banner."""
    console.print()
    console.rule("[bold green]Initialization Complete!", style="green")
    console.print()
    console.print("[bold green]✓ Project initialized successfully![/bold green]")
    console.print()
    console.print("[bold]Next:[/bold]")
    if not run_install:
        console.print("  • Run [cyan]make install[/cyan] to install project dependencies and build assets")
    if not run_doctor:
        console.print("  • Run [cyan]python manage.py doctor[/cyan] to verify setup")
    console.print("  • Review and update [cyan].env[/cyan] if needed")
    console.print("  • See [cyan]README.md[/cyan] for detailed setup instructions")
    console.print()

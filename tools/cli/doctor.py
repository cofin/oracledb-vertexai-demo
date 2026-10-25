# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Health check and diagnostics CLI command."""

from __future__ import annotations

import contextlib
import os
import shutil
from pathlib import Path
from typing import Any

import rich_click as click
from rich.console import Console

from app.utils.serialization import format_json
from tools.lib.utils import check_env_file, detect_deployment_mode, run_command
from tools.oracle.adb import ADB_FREE_CONTAINER_NAME, ADB_FREE_DEFAULT_IMAGE

__all__ = (
    "BYTES_PER_GIB",
    "MIN_RECOMMENDED_CPUS",
    "MIN_RECOMMENDED_MEM_BYTES",
    "MIN_RECOMMENDED_MEM_GIB",
    "console",
    "doctor_command",
)

BYTES_PER_GIB = 1024**3
MIN_RECOMMENDED_CPUS = 4
MIN_RECOMMENDED_MEM_GIB = 8
MIN_RECOMMENDED_MEM_BYTES = MIN_RECOMMENDED_MEM_GIB * BYTES_PER_GIB

console = Console()


@click.command(name="doctor")
@click.option(
    "--mode",
    type=click.Choice(["managed", "external"], case_sensitive=False),
    help="Check prerequisites for specific mode (auto-detect if not specified)",
)
@click.option("--json", "json_output", is_flag=True, help="Output results as JSON")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed diagnostic information")
def doctor_command(mode: str | None, json_output: bool, verbose: bool) -> None:
    """Verify local prerequisites, container resources, and ADB-Free wallet readiness."""
    resolved_mode = mode if mode is not None else detect_deployment_mode()

    if not json_output:
        console.rule(f"[bold blue]Health Check for '{resolved_mode}' Mode", style="blue")
        console.print()

    env_ok = _check_env_status(json_output=json_output)
    uv_ok = _check_uv_status(json_output=json_output, verbose=verbose)

    if not json_output:
        console.print(f"[yellow]🔧 Checking '{resolved_mode}' mode prerequisites...[/yellow]")

    checks: dict[str, Any] = {
        "mode": resolved_mode,
        "env_file": env_ok,
        "uv_installed": uv_ok,
        "mode_specific": {},
        "overall": False,
    }

    if resolved_mode == "managed":
        mode_specific, adb_free = _check_managed_mode(json_output=json_output)
        checks["mode_specific"] = mode_specific
        checks["adb_free"] = adb_free
    else:
        mode_specific = _check_external_mode(json_output=json_output)
        checks["mode_specific"] = mode_specific

    mode_checks = all(mode_specific.values()) if mode_specific else True
    checks["overall"] = env_ok and uv_ok and mode_checks

    if json_output:
        click.echo(format_json(checks, indent=2))
    else:
        _print_human_summary(checks)

    if not checks["overall"]:
        raise click.Abort


def _check_env_status(*, json_output: bool) -> bool:
    """Check whether ``.env`` exists and optionally print status."""
    if not json_output:
        console.print("[yellow]📄 Checking .env file...[/yellow]")
    exists = check_env_file()
    if not json_output:
        if exists:
            console.print("[green]✓ .env file exists[/green]")
        else:
            console.print("[red]✗ .env file not found[/red]")
            console.print("[dim]  Run: python manage.py init[/dim]")
    return exists


def _check_uv_status(*, json_output: bool, verbose: bool) -> bool:
    """Check whether ``uv`` is installed on ``PATH`` and optionally print version details."""
    if not json_output:
        console.print("[yellow]📦 Checking UV package manager...[/yellow]")
    uv_path = shutil.which("uv")
    installed = uv_path is not None
    if not json_output:
        if installed:
            returncode, stdout, _ = run_command(["uv", "--version"], check=False)
            version = stdout.strip() if returncode == 0 else "unknown"
            console.print(f"[green]✓ UV installed: {version}[/green]")
            if verbose:
                console.print(f"[dim]  Location: {uv_path}[/dim]")
        else:
            console.print("[red]✗ UV not found[/red]")
            console.print("[dim]  Run: make install-uv[/dim]")
    return installed


def _check_managed_mode(*, json_output: bool) -> tuple[dict[str, bool], dict[str, Any]]:
    """Inspect Docker/Podman runtime, CPU/memory thresholds, ``cymbal-adb-free``, and ``.envs/tns``."""
    has_docker = shutil.which("docker") is not None
    has_podman = shutil.which("podman") is not None
    runtime = "docker" if has_docker else ("podman" if has_podman else None)
    mode_specific = {"container_runtime": runtime is not None}

    container_name = os.getenv("ORACLE_CONTAINER_NAME", ADB_FREE_CONTAINER_NAME)
    wallet_dir = Path(os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN") or ".envs/tns")
    tnsnames_path = wallet_dir / "tnsnames.ora"
    https_port = os.getenv("ORACLE_HTTPS_PORT", "8443")
    apex_url = f"https://localhost:{https_port}/ords/apex"

    cpus, mem_total, container_running = _probe_container_runtime(runtime, container_name=container_name)
    adb_free: dict[str, Any] = {
        "image": os.getenv("ORACLE_IMAGE", ADB_FREE_DEFAULT_IMAGE),
        "container_name": container_name,
        "container_running": container_running,
        "cpus": cpus,
        "cpu_ok": cpus >= MIN_RECOMMENDED_CPUS,
        "memory_bytes": mem_total,
        "memory_ok": mem_total >= MIN_RECOMMENDED_MEM_BYTES,
        "wallet_tnsnames": str(tnsnames_path),
        "wallet_ready": tnsnames_path.is_file(),
        "apex_url": apex_url,
    }

    if not json_output:
        _print_managed_diagnostics(runtime=runtime, adb_free=adb_free)

    return mode_specific, adb_free


def _probe_container_runtime(runtime: str | None, *, container_name: str) -> tuple[int, int, bool]:
    """Query CPU count, total memory bytes, and ``container_name`` running state."""
    if runtime is None:
        return 0, 0, False

    cpu_fmt = "{{.NCPU}}" if runtime == "docker" else "{{.Host.CPUs}}"
    mem_fmt = "{{.MemTotal}}" if runtime == "docker" else "{{.Host.MemTotal}}"

    cpus = _query_int_metric([runtime, "info", "--format", cpu_fmt])
    mem_total = _query_int_metric([runtime, "info", "--format", mem_fmt])

    ret, stdout, _ = run_command([runtime, "inspect", "-f", "{{.State.Running}}", container_name], check=False)
    container_running = ret == 0 and stdout.strip().lower() == "true"
    return cpus, mem_total, container_running


def _query_int_metric(cmd: list[str]) -> int:
    """Execute ``cmd`` and parse an integer stdout value, returning ``0`` on failure."""
    ret, stdout, _ = run_command(cmd, check=False)
    if ret == 0:
        with contextlib.suppress(ValueError):
            return int(stdout.strip())
    return 0


def _print_managed_diagnostics(*, runtime: str | None, adb_free: dict[str, Any]) -> None:
    """Render human-readable diagnostics for managed ``adb-free:latest-26ai``."""
    if runtime == "docker":
        console.print("[green]✓ Docker found[/green]")
    elif runtime == "podman":
        console.print("[green]✓ Podman found[/green]")
    else:
        console.print("[red]✗ Neither Docker nor Podman found[/red]")
        console.print("[dim]  Install from: https://www.docker.com/get-started[/dim]")
        return

    cpus = int(adb_free["cpus"])
    if 0 < cpus < MIN_RECOMMENDED_CPUS:
        console.print(
            f"[yellow]⚠ Container runtime reports {cpus} CPUs "
            f"(recommend >= {MIN_RECOMMENDED_CPUS} CPUs for {ADB_FREE_DEFAULT_IMAGE})[/yellow]"
        )
    elif cpus >= MIN_RECOMMENDED_CPUS:
        console.print(f"[green]✓ Container runtime CPUs: {cpus} (>= {MIN_RECOMMENDED_CPUS})[/green]")

    mem_total = int(adb_free["memory_bytes"])
    if 0 < mem_total < MIN_RECOMMENDED_MEM_BYTES:
        console.print(
            f"[yellow]⚠ Allocated host memory is {mem_total / BYTES_PER_GIB:.2f} GiB "
            f"(recommend >= {MIN_RECOMMENDED_MEM_GIB} GiB for {ADB_FREE_DEFAULT_IMAGE})[/yellow]"
        )
    elif mem_total >= MIN_RECOMMENDED_MEM_BYTES:
        console.print(
            f"[green]✓ Container runtime memory: {mem_total / BYTES_PER_GIB:.2f} GiB "
            f"(>= {MIN_RECOMMENDED_MEM_GIB} GiB)[/green]"
        )

    container_name = str(adb_free["container_name"])
    apex_url = str(adb_free["apex_url"])
    if adb_free["container_running"]:
        console.print(f"[green]✓ ADB-Free container '{container_name}' is running (APEX: {apex_url})[/green]")
    else:
        console.print(
            f"[dim]i ADB-Free container '{container_name}' is not running yet "
            f"(run 'make start-infra' for {apex_url})[/dim]"
        )

    tnsnames_path = str(adb_free["wallet_tnsnames"])
    if adb_free["wallet_ready"]:
        console.print(f"[green]✓ Exported mTLS wallet ready: {tnsnames_path}[/green]")
    else:
        console.print(f"[dim]i Wallet {tnsnames_path} not exported yet (created by 'make start-infra')[/dim]")


def _check_external_mode(*, json_output: bool) -> dict[str, bool]:
    """Validate optional external wallet directory and required files."""
    mode_specific: dict[str, bool] = {}
    wallet_location = os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN")
    if not wallet_location:
        if not json_output:
            console.print("[dim]i No wallet configured (using standard connection)[/dim]")
        return mode_specific

    wallet_path = Path(wallet_location)
    wallet_exists = wallet_path.exists()
    wallet_valid = wallet_exists and (wallet_path / "cwallet.sso").exists() and (wallet_path / "tnsnames.ora").exists()
    mode_specific["wallet_configured"] = True
    mode_specific["wallet_exists"] = wallet_exists
    mode_specific["wallet_valid"] = wallet_valid

    if not json_output:
        console.print(f"[green]✓ Wallet location configured: {wallet_location}[/green]")
        if wallet_exists:
            console.print("[green]✓ Wallet directory exists[/green]")
            if wallet_valid:
                console.print("[green]✓ Wallet files valid[/green]")
            else:
                console.print("[red]✗ Wallet missing required files (cwallet.sso, tnsnames.ora)[/red]")
        else:
            console.print("[red]✗ Wallet directory not found[/red]")

    return mode_specific


def _print_human_summary(checks: dict[str, Any]) -> None:
    """Print overall doctor pass/fail summary and actionable remediation hints."""
    console.print()
    if checks["overall"]:
        console.print("[bold green]✓ All checks passed![/bold green]")
        console.print()
        console.print("[bold]Next steps:[/bold]")
        if checks.get("mode") == "managed":
            console.print("  • Run [cyan]make start-infra[/cyan] to start ADB-Free 26ai and export .envs/tns")
        console.print(
            "  • Run [cyan]uv run python manage.py database connect test[/cyan] to verify database connection"
        )
        console.print("  • Run [cyan]uv run coffee run[/cyan] to start the application")
        return

    console.print("[bold red]✗ Some checks failed[/bold red]")
    console.print()
    console.print("[bold]To fix:[/bold]")
    if not checks["env_file"]:
        console.print("  • Run [cyan]python manage.py init[/cyan]")
    if not checks["uv_installed"]:
        console.print("  • Run [cyan]make install-uv[/cyan]")
    mode_specific_dict = checks.get("mode_specific", {})
    if isinstance(mode_specific_dict, dict) and not all(mode_specific_dict.values()):
        console.print("  • Check mode-specific requirements above")

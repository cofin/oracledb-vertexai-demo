# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Click command group for VHS terminal and Playwright browser demo recordings (``manage.py demos``)."""

from __future__ import annotations

from pathlib import Path

import rich_click as click
from rich.console import Console

from tools.demos.shell import VHSRecorderConfig, VHSRecorderError, record_all_tapes, verify_vhs_prerequisites
from tools.demos.web import (
    WebDemoConfig,
    WebDemoError,
    WebDemoScenario,
    record_all_web_scenarios,
    verify_web_prerequisites,
)

__all__ = ("console", "demos_all", "demos_check", "demos_group", "demos_shell", "demos_web")

console = Console()


@click.group(name="demos")
def demos_group() -> None:
    """Record deterministic VHS terminal/SQLcl tapes and Playwright APEX 26.1 browser walkthroughs."""


@demos_group.command(name="check")
def demos_check() -> None:
    """Verify VHS, ttyd, FFmpeg, Chromium, and Playwright recording prerequisites."""
    try:
        vhs_bins = verify_vhs_prerequisites()
        web_bins = verify_web_prerequisites()
    except (VHSRecorderError, WebDemoError) as exc:
        console.print(f"[red]✗ Demo recording prerequisite check failed: {exc}[/red]", soft_wrap=True)
        raise click.Abort from exc

    console.print("[green]✓ All VHS shell and Playwright browser demo prerequisites are ready[/green]")
    for name, resolved in vhs_bins.items():
        console.print(f"  [bold]{name}:[/bold] {resolved}", soft_wrap=True)
    console.print(f"  [bold]playwright:[/bold] {web_bins['playwright']}", soft_wrap=True)


@demos_group.command(name="shell")
@click.option(
    "--tape",
    "tape_paths",
    type=click.Path(exists=True, dir_okay=False),
    multiple=True,
    help="Specific VHS .tape file(s) to record (defaults to all docs/_tapes/*.tape)",
)
def demos_shell(tape_paths: tuple[str, ...]) -> None:
    """Record VHS terminal and SQLcl walkthroughs to `.mp4` and `.gif`."""
    selected = tuple(Path(raw) for raw in tape_paths) if tape_paths else None
    try:
        results = record_all_tapes(config=VHSRecorderConfig(), tapes=selected)
    except VHSRecorderError as exc:
        console.print(f"[red]✗ VHS shell demo recording failed: {exc}[/red]", soft_wrap=True)
        raise click.Abort from exc

    for result in results:
        rendered = ", ".join(str(path) for path in result.outputs)
        console.print(f"[green]✓ Recorded {result.tape_path.name}:[/green] {rendered}", soft_wrap=True)


@demos_group.command(name="web")
@click.option(
    "--scenario",
    "scenario_names",
    type=click.Choice([item.value for item in WebDemoScenario], case_sensitive=False),
    multiple=True,
    help="Specific APEX 26.1 browser scenario(s) to record (defaults to all)",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False),
    default=None,
    help="Output directory for .mp4 and .gif demo artifacts (default docs/_static/demos)",
)
def demos_web(scenario_names: tuple[str, ...], output_dir: str | None) -> None:
    """Record headless Playwright + FFmpeg APEX 26.1 browser walkthroughs to `.mp4` and `.gif`."""
    resolved_dir = Path(output_dir) if output_dir else None
    selected = tuple(WebDemoScenario(name.lower()) for name in scenario_names) if scenario_names else None
    try:
        cfg = WebDemoConfig.from_env(output_dir=resolved_dir)
        results = record_all_web_scenarios(config=cfg, scenarios=selected)
    except WebDemoError as exc:
        console.print(f"[red]✗ Playwright web demo recording failed: {exc}[/red]", soft_wrap=True)
        raise click.Abort from exc

    for result in results:
        console.print(
            f"[green]✓ Recorded {result.scenario.value}:[/green] {result.mp4_path}, {result.gif_path}", soft_wrap=True
        )


@demos_group.command(name="all")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False),
    default=None,
    help="Output directory for web .mp4 and .gif demo artifacts (default docs/_static/demos)",
)
def demos_all(output_dir: str | None) -> None:
    """Record all VHS terminal tapes and Playwright APEX 26.1 browser walkthroughs."""
    resolved_dir = Path(output_dir) if output_dir else None
    try:
        verify_vhs_prerequisites()
        verify_web_prerequisites()
        shell_results = record_all_tapes(config=VHSRecorderConfig())
        web_results = record_all_web_scenarios(config=WebDemoConfig.from_env(output_dir=resolved_dir))
    except (VHSRecorderError, WebDemoError) as exc:
        console.print(f"[red]✗ Demo recording failed: {exc}[/red]", soft_wrap=True)
        raise click.Abort from exc

    for shell_res in shell_results:
        rendered = ", ".join(str(path) for path in shell_res.outputs)
        console.print(f"[green]✓ Recorded {shell_res.tape_path.name}:[/green] {rendered}", soft_wrap=True)
    for web_res in web_results:
        console.print(
            f"[green]✓ Recorded {web_res.scenario.value}:[/green] {web_res.mp4_path}, {web_res.gif_path}",
            soft_wrap=True,
        )

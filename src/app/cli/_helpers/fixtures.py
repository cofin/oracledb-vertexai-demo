# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Fixture lifecycle helpers for ``coffee`` CLI commands."""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any

from rich import get_console
from rich.table import Table

from app.db.utils import COFFEE_SHOP_TABLES, export_fixtures, load_fixtures
from app.lib.settings import get_settings
from app.utils.serialization import from_json


def display_fixture_list() -> None:
    """Display available fixture files."""
    console = get_console()
    console.rule("[bold blue]Available Fixture Files", style="blue", align="left")
    console.print()

    fixtures_dir = Path(get_settings().db.FIXTURE_PATH)
    if not fixtures_dir.exists():
        console.print(f"[yellow]Fixtures directory not found: {fixtures_dir}[/yellow]")
        return

    fixture_files = sorted(fixtures_dir.glob("*.json")) + sorted(fixtures_dir.glob("*.json.gz"))
    if not fixture_files:
        console.print("[yellow]No fixture files found in fixtures directory[/yellow]")
        return

    table = Table(show_header=True, header_style="bold blue", expand=True)
    table.add_column("Table", style="cyan", ratio=2)
    table.add_column("File", style="dim", ratio=3)
    table.add_column("Records", justify="right", ratio=1)
    table.add_column("Size", justify="right", ratio=1)
    table.add_column("Status", ratio=2)

    for fixture_file in fixture_files:
        table_name = fixture_file.name.replace(".json.gz", "").replace(".json", "")
        try:
            if fixture_file.suffix == ".gz":
                with gzip.open(fixture_file, "rb") as f:
                    data = from_json(f.read())
            else:
                data = from_json(fixture_file.read_text(encoding="utf-8"))

            records = str(len(data)) if isinstance(data, list) else "1"
            size_bytes = fixture_file.stat().st_size
            size_mb = size_bytes / 1024 / 1024
            size = f"{size_mb:.1f} MB" if size_mb > 1 else f"{size_bytes / 1024:.1f} KB"
            status = "[green]Ready[/green]"
        except (OSError, PermissionError, ValueError) as e:
            records = "[dim]N/A[/dim]"
            size = "[dim]N/A[/dim]"
            status = f"[red]Error: {e}[/red]"

        table.add_row(table_name, fixture_file.name, records, size, status)

    console.print(table)
    console.print()


async def load_fixture_data(tables: str | None) -> None:
    """Load fixture data into database."""
    console = get_console()
    console.rule("[bold blue]Loading Database Fixtures", style="blue", align="left")
    console.print()

    table_list = None
    if tables:
        table_list = [t.strip() for t in tables.split(",")]
        console.print(f"[dim]Loading specific tables: {', '.join(table_list)}[/dim]")
    else:
        console.print("[dim]Loading all available fixtures[/dim]")
    console.print()

    with console.status("[bold yellow]Loading fixtures...", spinner="dots"):
        results = await load_fixtures(table_list)

        if not results:
            console.print("[yellow]No fixture files found to load[/yellow]")
            return

        display_fixture_results(results)


def display_fixture_results(results: dict[str, Any]) -> None:
    """Display fixture loading results."""
    console = get_console()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Table", style="cyan", width=35)
    table.add_column("Status", width=100)

    total_upserted = 0
    total_failed = 0
    total_records = 0

    for table_name, result in results.items():
        row_data = process_fixture_result(table_name, result)
        table.add_row(row_data["row"][0], row_data["row"][4])

        total_upserted += row_data["upserted"]
        total_failed += row_data["failed"]
        total_records += row_data["total"]

    console.print(table)
    console.print()
    print_fixture_summary(total_upserted, total_failed, total_records)


def process_fixture_result(table_name: str, result: dict[str, Any] | str) -> dict[str, Any]:
    """Format a single fixture result row for the summary table."""
    if isinstance(result, dict):
        upserted = result.get("upserted", 0)
        failed = result.get("failed", 0)
        total = result.get("total", 0)
        error = result.get("error")
        status = get_fixture_status(upserted, failed, error)

        return {
            "row": [
                table_name,
                str(upserted) if upserted > 0 else "[dim]0[/dim]",
                str(failed) if failed > 0 else "[dim]0[/dim]",
                str(total),
                status,
            ],
            "upserted": upserted,
            "failed": failed,
            "total": total,
        }

    status = f"[red]✗ {result}[/red]"
    return {
        "row": [table_name, "[dim]0[/dim]", "[dim]0[/dim]", "[dim]0[/dim]", status],
        "upserted": 0,
        "failed": 0,
        "total": 0,
    }


def get_fixture_status(upserted: int, failed: int, error: str | None) -> str:
    """Render the colored status cell for a fixture-result row."""
    max_error_length = 500

    if upserted > 0 and failed == 0:
        return f"[green]✓ {upserted} upserted[/green]"
    if upserted > 0 and failed > 0:
        return f"[yellow]⚠ {upserted} upserted, {failed} failed[/yellow]"
    if failed > 0:
        status = f"[red]✗ {failed} failed[/red]"
        if error:
            if len(error) > max_error_length:
                status += f"\n[dim]{error[: max_error_length - 3]}...[/dim]"
            else:
                status += f"\n[dim]{error}[/dim]"
        return status
    return "[dim]Empty fixture[/dim]"


def print_fixture_summary(total_upserted: int, total_failed: int, total_records: int) -> None:
    """Print fixture loading summary."""
    console = get_console()
    console.print("[bold]Summary:[/bold]")
    console.print(f"  • [green]Upserted: {total_upserted}[/green]")
    if total_failed > 0:
        console.print(f"  • [red]Failed: {total_failed}[/red]")
    console.print(f"  • [dim]Total records in fixtures: {total_records}[/dim]")
    console.print()


def display_available_tables() -> None:
    """Display available tables for export."""
    console = get_console()
    console.rule("[bold blue]Available Tables for Export", style="blue", align="left")
    console.print()

    fixtures_dir = get_settings().db.FIXTURE_PATH
    table = Table(show_header=True, header_style="bold blue", expand=True)
    table.add_column("Table Name", style="cyan", ratio=2)
    table.add_column("Export Order", justify="center", ratio=1)

    for idx, table_name in enumerate(COFFEE_SHOP_TABLES, 1):
        table.add_row(table_name, str(idx))

    console.print(table)
    console.print()
    console.print(f"[dim]Default output directory: {fixtures_dir}[/dim]")
    console.print(f"[dim]Total tables: {len(COFFEE_SHOP_TABLES)}[/dim]")
    console.print()


async def export_fixture_data(tables: str | None, output_dir: str | None, no_compress: bool) -> None:
    """Export fixture data from database."""
    console = get_console()
    console.rule("[bold blue]Exporting Database Fixtures", style="blue", align="left")
    console.print()

    table_list = None
    if tables:
        table_list = [t.strip() for t in tables.split(",")]
        console.print(f"[dim]Exporting specific tables: {', '.join(table_list)}[/dim]")
    else:
        console.print("[dim]Exporting all available tables[/dim]")

    output_path = Path(output_dir) if output_dir else None
    if output_path:
        console.print(f"[dim]Output directory: {output_path}[/dim]")

    compress = not no_compress
    console.print(f"[dim]Compression: {'enabled' if compress else 'disabled'}[/dim]")
    console.print()

    with console.status("[bold yellow]Exporting fixtures...", spinner="dots"):
        results = await export_fixtures(table_list, output_path, compress)

        if not results:
            console.print("[yellow]No tables found to export[/yellow]")
            return

        display_export_results(results)


def display_export_results(results: dict[str, Any]) -> None:
    """Display fixture export results."""
    console = get_console()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Table", style="cyan", width=30)
    table.add_column("Output File", style="dim", width=50)
    table.add_column("Status", width=50)

    total_success = 0
    total_failed = 0

    for table_name, result in results.items():
        if isinstance(result, str):
            if result.startswith("/") or result.endswith((".json", ".json.gz")):
                status = "[green]✓ Exported[/green]"
                file_display = result
                total_success += 1
            else:
                status = f"[red]✗ Failed: {result}[/red]"
                file_display = "[dim]N/A[/dim]"
                total_failed += 1
        else:
            status = f"[yellow]⚠ Unknown result: {result}[/yellow]"
            file_display = "[dim]N/A[/dim]"
            total_failed += 1

        table.add_row(table_name, file_display, status)

    console.print(table)
    console.print()
    print_export_summary(total_success, total_failed)


def print_export_summary(total_success: int, total_failed: int) -> None:
    """Print fixture export summary."""
    console = get_console()
    console.print("[bold]Summary:[/bold]")
    console.print(f"  • [green]Successfully exported: {total_success} tables[/green]")
    if total_failed > 0:
        console.print(f"  • [red]Failed: {total_failed} tables[/red]")
    console.print()

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Substantial private workflows for ORDS/APEX configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import oracledb
from rich import get_console

from app.lib.settings import get_settings

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console


def parse_plsql_block(sql_path: Path) -> str:
    """Read the SQL file and return the PL/SQL block, stripping client-side settings."""
    if not sql_path.exists():
        msg = f"SQL file not found at {sql_path}"
        raise FileNotFoundError(msg)

    lines = []
    with sql_path.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            # Skip empty lines, SQL*Plus client settings, or comments
            if not stripped:
                continue
            if stripped.upper().startswith("SET "):
                continue
            if stripped == "/":
                continue
            lines.append(line)
    return "".join(lines)


def _run_block_and_fetch_output(connection: oracledb.Connection, plsql_block: str, console: Console) -> None:
    """Execute PL/SQL block and print DBMS_OUTPUT lines to the console."""
    with connection.cursor() as cursor:
        cursor.callproc("dbms_output.enable")
        console.print("[yellow]Executing APEX CDN configuration block...[/yellow]")
        cursor.execute(plsql_block)

        chunk_size = 100
        lines_var = cursor.arrayvar(str, chunk_size)
        num_lines_var = cursor.var(int)
        num_lines_var.setvalue(0, chunk_size)

        while True:
            cursor.callproc("dbms_output.get_lines", (lines_var, num_lines_var))
            num_lines = num_lines_var.getvalue()
            lines = lines_var.getvalue()[:num_lines]
            for line in lines:
                if line:
                    console.print(f"[DBMS_OUTPUT] {line}")
            if num_lines < chunk_size:
                break


def configure_apex_cdn_helper(system_password: str) -> None:
    """Connect as SYSDBA and run the APEX CDN configuration PL/SQL block."""
    console = get_console()
    settings = get_settings()

    # Locate configure-apex-cdn.sql
    from app.lib.settings import BASE_DIR

    sql_path = BASE_DIR.parents[1] / "tools" / "deploy" / "gcp" / "configure-apex-cdn.sql"

    console.print(f"[yellow]Reading SQL script from {sql_path.name}...[/yellow]")
    try:
        plsql_block = parse_plsql_block(sql_path)
    except Exception as e:
        console.print(f"[red]Error reading SQL script: {e}[/red]")
        raise

    dsn = settings.db.DSN
    console.print(f"[yellow]Connecting to {dsn} as SYSDBA...[/yellow]")

    try:
        connection = oracledb.connect(
            user="SYS",
            password=system_password,
            dsn=dsn,
            mode=oracledb.AUTH_MODE_SYSDBA,
        )
    except Exception as e:
        console.print(f"[red]Connection failed: {e}[/red]")
        raise

    try:
        with connection:
            _run_block_and_fetch_output(connection, plsql_block, console)
        console.print("[green]✓ APEX CDN configuration completed successfully![/green]")
    except Exception as e:
        console.print(f"[red]Execution failed: {e}[/red]")
        raise

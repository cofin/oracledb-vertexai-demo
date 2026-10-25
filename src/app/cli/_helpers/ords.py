# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Substantial private workflows for ORDS and APEX CDN configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import oracledb
from rich import get_console
from sqlspec.adapters.oracledb import extract_oracle_wallet_zip

from app.lib.settings import BASE_DIR, Settings

if TYPE_CHECKING:
    from rich.console import Console

__all__ = (
    "CONFIGURE_APEX_CDN_SQL",
    "DEPLOY_SQL_DIR",
    "REVERT_APEX_CDN_SQL",
    "configure_apex_cdn_helper",
    "parse_plsql_block",
)

DEPLOY_SQL_DIR = BASE_DIR / "db" / "sql" / "deploy"
CONFIGURE_APEX_CDN_SQL = DEPLOY_SQL_DIR / "configure-apex-cdn.sql"
REVERT_APEX_CDN_SQL = DEPLOY_SQL_DIR / "revert-apex-cdn.sql"
_DBMS_OUTPUT_CHUNK_SIZE = 100


def parse_plsql_block(sql_path: Path) -> str:
    """Read a packaged SQL file and return its PL/SQL block with SQL*Plus directives stripped."""
    if not sql_path.exists():
        msg = f"SQL file not found at {sql_path}"
        raise FileNotFoundError(msg)

    lines: list[str] = []
    with sql_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.upper().startswith("SET "):
                continue
            if stripped == "/":
                continue
            lines.append(line)
    return "".join(lines)


def configure_apex_cdn_helper(system_password: str | None = None) -> None:
    """Connect as `ADMIN` (Autonomous wallet) or `SYSDBA` and run the APEX CDN PL/SQL block."""
    console = get_console()
    settings = Settings.from_env()
    connect_banner, connect_params = _build_ords_connect_params(settings, system_password=system_password)

    sql_path = CONFIGURE_APEX_CDN_SQL
    console.print(f"[yellow]Reading SQL script from {sql_path.name}...[/yellow]")
    try:
        plsql_block = parse_plsql_block(sql_path)
    except Exception as exc:
        console.print(f"[red]Error reading SQL script: {exc}[/red]")
        raise

    console.print(f"[yellow]{connect_banner}[/yellow]")
    try:
        connection = oracledb.connect(**connect_params)
    except Exception as exc:
        console.print(f"[red]Connection failed: {exc}[/red]")
        raise

    try:
        with connection:
            _run_block_and_fetch_output(connection, plsql_block, console)
        console.print("[green]✓ APEX CDN configuration completed successfully![/green]")
    except Exception as exc:
        console.print(f"[red]Execution failed: {exc}[/red]")
        raise


def _build_ords_connect_params(settings: Settings, *, system_password: str | None) -> tuple[str, dict[str, Any]]:
    """Build `oracledb.connect` arguments for Autonomous `ADMIN` wallet or standard `SYSDBA` mode."""
    if settings.db.is_autonomous:
        if not settings.db.WALLET_LOCATION:
            msg = "WALLET_LOCATION or TNS_ADMIN environment variable must be set for Autonomous Database"
            raise ValueError(msg)

        conn_params = settings.db.get_connection_params()
        dsn = str(conn_params["dsn"])
        admin_password = (
            system_password
            or os.getenv("DATABASE_ADMIN_PASSWORD")
            or os.getenv("ORACLE_ADMIN_PASSWORD")
            or settings.db.PASSWORD
        )
        wallet_password = settings.db.WALLET_PASSWORD
        resolved_wallet = extract_oracle_wallet_zip(Path(settings.db.WALLET_LOCATION), wallet_password=wallet_password)
        wallet_dir = str(resolved_wallet)
        params: dict[str, Any] = {
            "user": "ADMIN",
            "password": admin_password,
            "dsn": dsn,
            "config_dir": wallet_dir,
            "wallet_location": wallet_dir,
        }
        if wallet_password:
            params["wallet_password"] = wallet_password
        return f"Connecting to {dsn} as ADMIN with wallet...", params

    resolved_password = system_password or os.getenv("DATABASE_SYSTEM_PASSWORD") or os.getenv("ORACLE_SYSTEM_PASSWORD")
    if not resolved_password:
        msg = "DATABASE_SYSTEM_PASSWORD environment variable is not set"
        raise ValueError(msg)

    dsn = settings.db.DSN
    return f"Connecting to {dsn} as SYSDBA...", {
        "user": "SYS",
        "password": resolved_password,
        "dsn": dsn,
        "mode": oracledb.AUTH_MODE_SYSDBA,
    }


def _run_block_and_fetch_output(connection: oracledb.Connection, plsql_block: str, console: Console) -> None:
    """Execute a PL/SQL block and stream `DBMS_OUTPUT` lines to the console."""
    with connection.cursor() as cursor:
        cursor.callproc("dbms_output.enable")
        console.print("[yellow]Executing APEX CDN configuration block...[/yellow]")
        cursor.execute(plsql_block)

        lines_var = cursor.arrayvar(str, _DBMS_OUTPUT_CHUNK_SIZE)
        num_lines_var = cursor.var(int)
        num_lines_var.setvalue(0, _DBMS_OUTPUT_CHUNK_SIZE)

        while True:
            cursor.callproc("dbms_output.get_lines", (lines_var, num_lines_var))
            num_lines = int(num_lines_var.getvalue())
            lines = lines_var.getvalue()[:num_lines]
            for line in lines:
                if line:
                    console.print(f"[DBMS_OUTPUT] {line}")
            if num_lines < _DBMS_OUTPUT_CHUNK_SIZE:
                break

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle APEX status, OpenAPI catalog, and APEXlang CLI commands (``manage.py infra apex``)."""

from __future__ import annotations

import http.client
import ssl
from pathlib import Path
from typing import Any

import oracledb
import rich_click as click
from rich.console import Console
from sqlspec.adapters.oracledb import extract_oracle_wallet_zip

from tools.oracle.apex_catalog import DEFAULT_APEX_OPENAPI_PATH, export_current_app_apex_catalog
from tools.oracle.apex_lang import ApexLang, ApexLangConfig
from tools.oracle.connection import ConnectionConfig
from tools.oracle.database import ContainerFlavor, DatabaseConfig
from tools.oracle.sqlcl_installer import SQLclInstaller

__all__ = (
    "apex_export",
    "apex_export_openapi",
    "apex_generate",
    "apex_group",
    "apex_import",
    "apex_status",
    "apex_validate",
    "console",
)

_HTTP_OK_MIN = 200
_HTTP_SERVER_ERROR_MIN = 500

console = Console()


@click.group(name="apex")
def apex_group() -> None:
    """Inspect Oracle APEX 26.1, export REST catalogs, and manage APEXlang sources."""


@apex_group.command(name="status")
def apex_status() -> None:
    """Report the live APEX_RELEASE version and ORDS HTTPS endpoint readiness."""
    try:
        _render_apex_status()
    except Exception as exc:
        console.print(f"[red]✗ Failed to read APEX status: {exc}[/red]")
        raise click.Abort from exc


@apex_group.command(name="export-openapi")
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False),
    default=str(DEFAULT_APEX_OPENAPI_PATH),
    show_default=True,
    help="OpenAPI catalog JSON artifact path",
)
@click.option(
    "--server-url",
    default=None,
    help="Base URL APEX should use for the Litestar app (default APP_URL or http://host.docker.internal:8000)",
)
def apex_export_openapi(output_path: str, server_url: str | None) -> None:
    """Export the /api/apex OpenAPI subset for APEX REST Source Catalog import."""
    try:
        catalog_path = export_current_app_apex_catalog(output_path=Path(output_path), server_url=server_url)
        console.print(f"[green]✓ Exported APEX OpenAPI catalog to {catalog_path}[/green]")
    except Exception as exc:
        console.print(f"[red]✗ APEX OpenAPI export failed: {exc}[/red]")
        raise click.Abort from exc


@apex_group.command(name="generate")
@click.option("--alias", "app_alias", default="cymbal-coffee-ops", show_default=True, help="APEX app alias")
@click.option("--app-name", default=None, help="Starter application display name")
@click.option("--app-id", type=int, default=None, help="Starter application ID")
@click.option("--workspace", default=None, help="APEX workspace name")
@click.option("--schema", default=None, help="Parsing schema")
@click.option("--force", is_flag=True, help="Remove and recreate existing generated files")
def apex_generate(
    app_alias: str, app_name: str | None, app_id: int | None, workspace: str | None, schema: str | None, force: bool
) -> None:
    """Generate starter APEXlang source files with SQLcl 26.1.2+ against APEX 26.1+."""
    try:
        result = _build_apex_lang().generate(
            alias=app_alias, app_name=app_name, app_id=app_id, workspace=workspace, schema=schema, force=force
        )
        console.print(f"[green]✓ Generated APEXlang source at {result.target_path}[/green]")
    except Exception as exc:
        console.print(f"[red]✗ APEXlang generate failed: {exc}[/red]")
        raise click.Abort from exc


@apex_group.command(name="export")
@click.option("--app-id", type=int, required=True, help="APEX application ID to export")
@click.option("--alias", "app_alias", default="cymbal-coffee-ops", show_default=True, help="APEX app alias")
@click.option("--clean/--no-clean", default=True, show_default=True, help="Use SQLcl -force for stable output")
def apex_export(app_id: int, app_alias: str, clean: bool) -> None:
    """Export an existing APEX 26.1+ app as APEXlang source with SQLcl 26.1.2+."""
    try:
        result = _build_apex_lang().export(app_id=app_id, alias=app_alias, clean=clean)
        console.print(f"[green]✓ Exported APEXlang source to {result.target_path}[/green]")
    except Exception as exc:
        console.print(f"[red]✗ APEXlang export failed: {exc}[/red]")
        raise click.Abort from exc


@apex_group.command(name="validate")
@click.option("--alias", "app_alias", default="cymbal-coffee-ops", show_default=True, help="APEX app alias")
@click.option("--input", "input_path", type=click.Path(), default=None, help="APEXlang input path")
@click.option("--workspace", default=None, help="APEX workspace name")
@click.option("--deployment", default=None, help="Deployment file name or path")
@click.option("--debug", is_flag=True, help="Enable SQLcl APEX validation debug output")
def apex_validate(
    app_alias: str, input_path: str | None, workspace: str | None, deployment: str | None, debug: bool
) -> None:
    """Validate APEXlang source with SQLcl 26.1.2+ against APEX 26.1+."""
    try:
        result = _build_apex_lang().validate(
            alias=app_alias,
            input_path=Path(input_path) if input_path else None,
            workspace=workspace,
            deployment=deployment,
            debug=debug,
        )
        console.print(f"[green]✓ Validated APEXlang source at {result.target_path}[/green]")
    except Exception as exc:
        console.print(f"[red]✗ APEXlang validation failed: {exc}[/red]")
        raise click.Abort from exc


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
    """Import APEXlang source into APEX 26.1+ with SQLcl 26.1.2+."""
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
    except Exception as exc:
        console.print(f"[red]✗ APEXlang import failed: {exc}[/red]")
        raise click.Abort from exc


def _build_apex_lang() -> ApexLang:
    """Build the SQLcl-backed APEXlang workflow wrapper."""
    return ApexLang(installer=SQLclInstaller(console=console), config=ApexLangConfig.from_env(), console=console)


def _render_apex_status() -> None:
    """Query ``APEX_RELEASE``, probe ORDS HTTPS, and print endpoint URLs."""
    db_config = DatabaseConfig.from_env()
    conn_config = ConnectionConfig.from_env()
    version_no, api_compat = _query_apex_release(db_config, conn_config)
    ords_ready = _probe_ords_https(db_config.https_port)
    ords_base = f"https://localhost:{db_config.https_port}/ords"
    ords_state = "[green]ready[/green]" if ords_ready else "[yellow]unreachable[/yellow]"
    console.print(f"[bold]APEX Release:[/bold] {version_no} (API: {api_compat})")
    console.print(f"[bold]ORDS HTTPS:[/bold] {ords_base}/ ({ords_state})")
    console.print(f"[bold]APEX Builder:[/bold] {ords_base}/apex")
    console.print(f"[bold]Workspace:[/bold] {db_config.workspace_name} (user: {db_config.app_user.upper()})")
    console.print(f"[bold]Database Actions:[/bold] {ords_base}/sql-developer")


def _resolve_status_connection_params(db_config: DatabaseConfig, conn_config: ConnectionConfig) -> dict[str, Any]:
    """Build ``python-oracledb`` connection parameters for the ``APEX_RELEASE`` status query."""
    user = conn_config.user or db_config.app_user
    password = conn_config.password or db_config.app_user_password

    wallet_dir = conn_config.wallet_location
    if wallet_dir is None and db_config.flavor == ContainerFlavor.ADB_FREE and not conn_config.host:
        wallet_dir = db_config.wallet_dir

    if wallet_dir is not None:
        wallet_pw = conn_config.wallet_password or db_config.wallet_password
        if wallet_dir.is_file() and wallet_dir.suffix == ".zip":
            resolved_wallet = extract_oracle_wallet_zip(wallet_dir, wallet_password=wallet_pw)
            wallet_path = str(resolved_wallet)
        else:
            wallet_path = str(wallet_dir.resolve())
        service_dsn = conn_config.dsn or (
            conn_config.service_name
            if conn_config.service_name and conn_config.service_name != "freepdb1"
            else db_config.service_name
        )
        params: dict[str, Any] = {
            "user": user,
            "password": password,
            "dsn": service_dsn,
            "config_dir": wallet_path,
            "wallet_location": wallet_path,
        }
        if wallet_pw:
            params["wallet_password"] = wallet_pw
        return params

    return {"user": user, "password": password, "dsn": conn_config.get_dsn()}


def _query_apex_release(db_config: DatabaseConfig, conn_config: ConnectionConfig) -> tuple[str, str]:
    """Query ``APEX_RELEASE`` via ``oracledb`` and return ``(version_no, api_compatibility)``."""
    params = _resolve_status_connection_params(db_config, conn_config)
    with oracledb.connect(**params) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT VERSION_NO, API_COMPATIBILITY FROM APEX_RELEASE")
        row = cursor.fetchone()
    if not row:
        return ("not installed", "unknown")
    version_no = str(row[0]) if row[0] is not None else "not installed"
    api_compat = str(row[1]) if len(row) > 1 and row[1] is not None else "unknown"
    return (version_no, api_compat)


def _probe_ords_https(https_port: int) -> bool:
    """Return True when ORDS responds on ``https://localhost:<https_port>/ords/``."""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    conn = http.client.HTTPSConnection("localhost", https_port, timeout=5, context=ssl_context)
    try:
        conn.request("GET", "/ords/")
        response = conn.getresponse()
        return _HTTP_OK_MIN <= response.status < _HTTP_SERVER_ERROR_MIN
    except Exception:
        return False
    finally:
        conn.close()

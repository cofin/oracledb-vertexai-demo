#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Cymbal Coffee Infrastructure and Database Lifecycle Management.

Unified DevOps CLI for the Oracle 26ai + Vertex AI demo exposing ``init``,
``install``, ``doctor``, ``infra``, ``database``, ``assets``, and ``slides``.

Examples::

    python manage.py init
    python manage.py install all
    python manage.py doctor
    python manage.py infra start
    python manage.py infra apex status
    python manage.py database upgrade
    python manage.py database wallet configure
    python manage.py assets build
"""

from __future__ import annotations

import sys
from pathlib import Path

import rich_click as click
from dotenv import load_dotenv
from litestar.cli._utils import LitestarEnv
from litestar_vite.cli import vite_group
from rich.console import Console
from sqlspec.cli import add_migration_commands
from tools.cli import doctor_command, init_command, install_group
from tools.oracle import apex_group as oracle_apex_group
from tools.oracle import connect_group as oracle_connect_group
from tools.oracle import database_group as oracle_container_group
from tools.oracle import wallet_group as oracle_wallet_group
from tools.slides import slides_group

from app import config as app_config
from app.__metadata__ import __version__

__all__ = ("assets_group", "cli", "console", "database_group", "infra_group", "main")

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "yellow italic"
click.rich_click.ERRORS_SUGGESTION = "Try running the '--help' flag for more information."

console = Console()

_INFRA_RENAME = {
    "start": "start",
    "stop": "stop",
    "restart": "restart",
    "status": "status",
    "logs": "logs",
    "remove": "wipe",
}
_VITE_ASSET_COMMANDS = frozenset({"install", "generate-types", "build", "serve"})


@click.group(
    help="""
    [bold cyan]Cymbal Coffee Infrastructure and Database Management[/bold cyan]

    Unified DevOps CLI for the Oracle 26ai + Vertex AI demo.
    """,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version=__version__, prog_name="manage")
def cli() -> None:
    """Top-level entry point."""
    _load_default_env()


cli.add_command(init_command, name="init")
cli.add_command(install_group, name="install")
cli.add_command(doctor_command, name="doctor")
cli.add_command(slides_group, name="slides")


@cli.group(name="infra", help="Manage development infrastructure (Oracle AI Database 26ai container & APEX).")
def infra_group() -> None:
    """Oracle AI Database 26ai container and APEX lifecycle commands."""


for _src_name, _dst_name in _INFRA_RENAME.items():
    _infra_cmd = oracle_container_group.commands.get(_src_name)
    if _infra_cmd is not None:
        infra_group.add_command(_infra_cmd, name=_dst_name)

infra_group.add_command(oracle_apex_group, name="apex")


@cli.group(name="database", help="Database management — migrations, wallet, and connection tests.")
@click.pass_context
def database_group(ctx: click.Context) -> None:
    """Database administration. Migration commands work against ``app.config.db``."""
    ctx.ensure_object(dict)
    ctx.obj["configs"] = [app_config.db]


database_group.add_command(oracle_wallet_group, name="wallet")
database_group.add_command(oracle_connect_group, name="connect")
add_migration_commands(database_group)


@cli.group(name="assets", help="Frontend asset pipeline (Vite via litestar-vite).")
@click.pass_context
def assets_group(ctx: click.Context) -> None:
    """Wire a LitestarEnv factory onto ``ctx.obj`` for the Vite subcommands."""
    ctx.obj = _get_litestar_env


for _vite_name, _vite_cmd in vite_group.commands.items():
    if _vite_name in _VITE_ASSET_COMMANDS:
        assets_group.add_command(_vite_cmd, name=_vite_name)


def main() -> None:
    """Dispatch the unified management CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)


def _load_default_env() -> None:
    """Load ``.env`` from the working directory without overriding explicit shell variables."""
    env_path = Path(".env")
    if env_path.is_file():
        load_dotenv(env_path, override=False)


def _get_litestar_env() -> LitestarEnv:
    """Load the Litestar application environment for Vite asset commands."""
    return LitestarEnv.from_env("app.server.asgi:create_app")


if __name__ == "__main__":
    main()

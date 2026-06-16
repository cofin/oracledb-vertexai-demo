#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Cymbal Coffee Infrastructure and Database Lifecycle Management.

Unified DevOps CLI for the Oracle 26ai + Vertex AI demo. Mirrors the
``dma/accelerator`` layout: six top-level groups (``init``, ``install``,
``doctor``, ``infra``, ``database``, ``assets``).

Examples::

    python manage.py init
    python manage.py install all
    python manage.py doctor
    python manage.py infra start
    python manage.py database upgrade
    python manage.py database wallet locate
    python manage.py assets build
"""

from __future__ import annotations

import sys

import rich_click as click
from rich.console import Console
from tools.cli import doctor_command, init_command, install_group
from tools.oracle import (
    apex_group as oracle_apex_group,
)
from tools.oracle import (
    connect_group as oracle_connect_group,
)
from tools.oracle import (
    database_group as oracle_container_group,
)
from tools.oracle import (
    wallet_group as oracle_wallet_group,
)

from app.__metadata__ import __version__

# rich-click config
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "yellow italic"
click.rich_click.ERRORS_SUGGESTION = "Try running the '--help' flag for more information."

console = Console()


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


# Project lifecycle
cli.add_command(init_command, name="init")
cli.add_command(install_group, name="install")
cli.add_command(doctor_command, name="doctor")


# =============================================================================
# Infrastructure (flat — start/stop/restart/status/logs/wipe)
# =============================================================================


@cli.group(name="infra", help="Manage development infrastructure (Oracle 26ai container).")
def infra_group() -> None:
    """Oracle 26ai container lifecycle — flat namespace, accelerator-style."""


_INFRA_RENAME = {
    "start": "start",
    "stop": "stop",
    "restart": "restart",
    "status": "status",
    "logs": "logs",
    "remove": "wipe",
}
for src_name, dst_name in _INFRA_RENAME.items():
    cmd = oracle_container_group.commands.get(src_name)
    if cmd is not None:
        infra_group.add_command(cmd, name=dst_name)

# APEX install/upgrade/status as a nested subgroup: `manage.py infra apex …`
infra_group.add_command(oracle_apex_group, name="apex")


# =============================================================================
# Database (sqlspec migrations + wallet + connect)
# =============================================================================


@cli.group(name="database", help="Database management — migrations, wallet, and connection tests.")
@click.pass_context
def database_group(ctx: click.Context) -> None:
    """Database administration. Migration commands work against ``app.config.db``."""
    import app.config as app_config  # mypy needs explicit submodule import (not `from app import config`).

    ctx.ensure_object(dict)
    ctx.obj["configs"] = [app_config.db]


database_group.add_command(oracle_wallet_group, name="wallet")
database_group.add_command(oracle_connect_group, name="connect")


# =============================================================================
# Assets (litestar-vite passthrough)
# =============================================================================


@cli.group(name="assets", help="Frontend asset pipeline (Vite via litestar-vite).")
@click.pass_context
def assets_group(ctx: click.Context) -> None:
    """Wire a LitestarEnv factory onto ctx.obj for the Vite subcommands."""
    from litestar.cli._utils import LitestarEnv

    def _get_env() -> LitestarEnv:
        return LitestarEnv.from_env("app.server.asgi:create_app")

    ctx.obj = _get_env


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Bootstrap migration + Vite subcommands then dispatch."""
    from litestar_vite.cli import vite_group
    from sqlspec.cli import add_migration_commands

    add_migration_commands(database_group)
    for name, command in vite_group.commands.items():
        if name in {"install", "generate-types", "build", "serve"}:
            assets_group.add_command(command, name=name)

    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()

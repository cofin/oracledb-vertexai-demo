# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Database migration helpers for ``coffee`` CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from rich import get_console
from sqlspec.migrations.commands import create_migration_commands

import app.config as app_config
from app.cli._helpers.fixtures import display_fixture_results
from app.db.utils import load_fixtures

if TYPE_CHECKING:
    from sqlspec.migrations.commands import AsyncMigrationCommands


async def upgrade_database(revision: str, no_fixtures: bool, dry_run: bool) -> None:
    """Upgrade database to a specific revision and optionally load fixtures."""
    console = get_console()
    console.rule("[bold blue]Database Upgrade", style="blue", align="left")
    console.print()

    migration_commands = cast("AsyncMigrationCommands[Any]", create_migration_commands(config=app_config.db))
    await migration_commands.upgrade(revision=revision, dry_run=dry_run)

    if dry_run:
        console.print("[yellow]i[/yellow]  Dry run — skipping fixture load")
        return
    if no_fixtures:
        console.print("[yellow]i[/yellow]  Skipping fixture load (--no-fixtures)")
        return

    with console.status("[bold yellow]Loading fixtures...", spinner="dots"):
        results = await load_fixtures(None)
        if not results:
            console.print("[yellow]No fixture files found to load[/yellow]")
        else:
            display_fixture_results(results)
    console.print()


async def downgrade_database(revision: str, dry_run: bool) -> None:
    """Downgrade database to a specific revision."""
    console = get_console()
    console.rule("[bold blue]Database Downgrade", style="blue", align="left")
    console.print()

    migration_commands = cast("AsyncMigrationCommands[Any]", create_migration_commands(config=app_config.db))
    await migration_commands.downgrade(revision=revision, dry_run=dry_run)
    console.print()

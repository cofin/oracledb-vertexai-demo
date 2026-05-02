# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Cache lifecycle helpers for ``coffee`` CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich import get_console
from rich.prompt import Prompt

if TYPE_CHECKING:
    from app.domain.system.services import CacheService


async def clear_application_cache(force: bool, cache_service: CacheService) -> None:
    """Clear application caches."""
    console = get_console()

    if not force:
        console.print("[bold]Tables to clear:[/bold]")
        for table in ("response_cache", "embedding_cache"):
            console.print(f"  • {table}")

        confirm = Prompt.ask(
            "\n[bold red]Are you sure you want to clear these caches?[/bold red]",
            choices=["y", "n"],
            default="n",
        )
        if confirm.lower() != "y":
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

    console.rule("[bold blue]Clearing Caches", style="blue", align="left")
    console.print()
    deleted_count = await cache_service.invalidate_cache()
    console.print(f"[green]✓ Cleared {deleted_count} cache records[/green]")
    console.print()

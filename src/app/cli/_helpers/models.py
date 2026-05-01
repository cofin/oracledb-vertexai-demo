# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Model information helpers for ``coffee`` CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich import get_console

from app.lib.settings import get_settings

if TYPE_CHECKING:
    from app.domain.products.services import VertexAIService


def show_model_info(vertex_ai_service: VertexAIService) -> None:
    """Show information about currently configured AI models."""
    settings = get_settings()
    console = get_console()
    console.rule("[bold blue]AI Model Configuration", style="blue", align="left")
    console.print()

    console.print(f"[bold]Chat Model:[/bold] {settings.vertex_ai.CHAT_MODEL}")
    console.print(f"[bold]Embedding Model:[/bold] {settings.vertex_ai.EMBEDDING_MODEL}")
    console.print(f"[bold]Google Project:[/bold] {settings.vertex_ai.PROJECT_ID}")
    console.print(f"[bold]Embedding Dimensions:[/bold] {settings.vertex_ai.EMBEDDING_DIMENSIONS}")
    console.print()

    console.print("[bold]🔍 Testing Model Initialization...[/bold]")
    _ = vertex_ai_service.client
    console.print("[bold green]✓ Successfully initialized![/bold green]")
    console.print()

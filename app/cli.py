# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line interface."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import anyio
import click
import structlog
from click import Context
from rich import get_console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner

from app.__metadata__ import __version__

if TYPE_CHECKING:
    from typing import Any

    from rich.console import Console

    from app.services import RecommendationService


__all__ = ["bulk_embed", "embed_new", "load_fixtures", "load_vectors", "model_info", "recommend", "version_callback"]

logger = structlog.get_logger()


def version_callback(ctx: Context, _: click.Parameter, value: bool) -> None:
    if value and not ctx.resilient_parsing:
        click.echo(f"{__version__}")
        ctx.exit()


@click.command(name="recommend", help="Find a coffee.")
def recommend() -> None:
    """Execute the recommendation engine from the CLI"""
    import anyio
    from rich import get_console

    async def _get_recommendations() -> None:
        from rich import get_console

        from app.config import alchemy
        from app.server.deps import (
            provide_product_service,
            provide_shop_service,
        )
        from app.services import (
            ChatConversationService,
            IntentExemplarService,
            OracleVectorSearchService,
            RecommendationService,
            ResponseCacheService,
            SearchMetricsService,
            UserSessionService,
            VertexAIService,
        )

        console = get_console()
        engine = alchemy.get_engine()
        async with alchemy.get_session() as db_session:
            shops_service = await anext(provide_shop_service(db_session))
            products_service = await anext(provide_product_service(db_session))

            # Initialize Vertex AI and Oracle services
            vertex_ai_service = VertexAIService()
            session_service = UserSessionService(session=db_session)
            conversation_service = ChatConversationService(session=db_session)
            cache_service = ResponseCacheService(session=db_session)
            metrics_service = SearchMetricsService(session=db_session)
            exemplar_service = IntentExemplarService(session=db_session)

            vector_search_service = OracleVectorSearchService(
                products_service=products_service,
                vertex_ai_service=vertex_ai_service,
            )

            service = RecommendationService(
                vertex_ai_service=vertex_ai_service,
                vector_search_service=vector_search_service,
                products_service=products_service,
                shops_service=shops_service,
                session_service=session_service,
                conversation_service=conversation_service,
                cache_service=cache_service,
                metrics_service=metrics_service,
                exemplar_service=exemplar_service,
                user_id="cli-0",
            )

            await _chat_session(service=service, console=console)

        await engine.dispose()

    console = get_console()
    console.print(
        dedent(
            """
    [bold cyan]🚀 Welcome to the Cymbal Coffee Recommendation Engine! 🚀[/bold cyan]
    Type your questions about coffee below.
    Type [bold red]"/stop"[/bold red] to exit.
    """,
        ),
    )
    anyio.run(_get_recommendations)


async def _chat_session(
    service: RecommendationService,
    console: Any,
) -> None:
    """Handle a chat session"""
    while True:
        message = Prompt.ask("[bold cyan]You[/bold cyan]")
        if message == "/stop":
            break
        console.print("[bold magenta]Cymbal AI[/bold magenta]: thinking...")
        await query_recommendation(service, message)


async def query_recommendation(
    service: RecommendationService,
    message: str,
    panel: bool = True,
) -> None:
    """Execute the recommendation"""

    class NoPadding:
        def __init__(self, renderable: Any) -> None:
            self.renderable = renderable

        def __rich_console__(self, console: Console, options: Any) -> Any:
            yield self.renderable

    console = get_console()

    with Live(Spinner("aesthetic"), refresh_per_second=15, console=console, transient=True):
        response = await service.get_recommendation(message)
        text = response.answer
        console.print_json(data={"answer": response.answer, "query_id": response.query_id})
        if panel:
            console.print(Panel(Markdown(text), title="🤖 Cymbal AI", title_align="left"))
        else:
            console.print(NoPadding(Markdown(text)))


# Individual CLI functions - these will be added to Litestar's CLI by the plugin


@click.command()
def load_fixtures() -> None:
    """Load coffee demo fixture data."""
    from app.db.utils import load_database_fixtures

    anyio.run(load_database_fixtures)


@click.command()
def load_vectors() -> None:
    """Generate and load vector embeddings for products."""
    from app.db.utils import _load_vectors

    anyio.run(_load_vectors)


@click.command()
def bulk_embed() -> None:
    """Run bulk embedding job for all products using Vertex AI Batch Prediction."""

    async def _run_bulk_embed() -> None:
        from app.config import alchemy
        from app.server.deps import provide_product_service
        from app.services.bulk_embedding import BulkEmbeddingService

        console = get_console()
        console.print("[bold cyan]🚀 Starting bulk embedding job...[/bold cyan]")

        async with alchemy.get_session() as db_session:
            products_service = await anext(provide_product_service(db_session))
            bulk_service = BulkEmbeddingService(products_service)

            # Run the complete bulk embedding pipeline
            result = await bulk_service.run_bulk_embedding_job()

            if result["status"] == "completed":
                console.print("[bold green]✓ Bulk embedding completed![/bold green]")
                console.print(f"Products exported: {result['products_exported']}")
                console.print(f"Embeddings processed: {result['embeddings_processed']}")
                console.print(f"Job ID: {result['job_id']}")
            elif result["status"] == "skipped":
                console.print(f"[yellow]⚠ {result['reason']}[/yellow]")
            else:
                console.print(f"[bold red]✗ Bulk embedding failed: {result['error']}[/bold red]")

    anyio.run(_run_bulk_embed)


@click.command()
@click.option("--limit", default=200, help="Maximum number of products to process in this batch (default: 200)")
def embed_new(limit: int) -> None:
    """Process new/updated products using online embedding API for real-time updates."""

    async def _embed_new_products() -> None:
        from app.config import alchemy
        from app.server.deps import provide_product_service
        from app.services.bulk_embedding import OnlineEmbeddingService
        from app.services.vertex_ai import VertexAIService

        console = get_console()
        console.print(f"[bold cyan]🔄 Processing up to {limit} new products...[/bold cyan]")

        async with alchemy.get_session() as db_session:
            products_service = await anext(provide_product_service(db_session))
            vertex_ai_service = VertexAIService()
            online_service = OnlineEmbeddingService(vertex_ai_service)

            # Process new products
            processed_count = await online_service.process_new_products(products_service)

            if processed_count > 0:
                console.print(f"[bold green]✓ Processed {processed_count} products![/bold green]")
            else:
                console.print("[yellow]No new products to process[/yellow]")

    anyio.run(_embed_new_products)


@click.command()
def model_info() -> None:
    """Show information about currently configured AI models."""

    def _show_model_info() -> None:
        from app.lib.settings import get_settings
        from app.services.vertex_ai import VertexAIService

        console = get_console()
        console.print("[bold cyan]🤖 AI Model Configuration[/bold cyan]")

        # Show settings
        settings = get_settings()
        console.print(f"[bold]Configured Model:[/bold] {settings.app.GEMINI_MODEL}")
        console.print(f"[bold]Embedding Model:[/bold] {settings.app.EMBEDDING_MODEL}")
        console.print(f"[bold]Google Project:[/bold] {settings.app.GOOGLE_PROJECT_ID}")

        # Test model initialization
        console.print("\n[bold cyan]🔍 Testing Model Initialization...[/bold cyan]")
        try:
            vertex_service = VertexAIService()
            model_info = vertex_service.get_model_info()

            console.print("[bold green]✓ Successfully initialized![/bold green]")
            console.print(f"[bold]Active Model:[/bold] {model_info['active_model']}")

            # Show additional details
            console.print(f"[dim]Full model path: {model_info['active_model_full']}[/dim]")

        except Exception as e:  # noqa: BLE001
            console.print(f"[bold red]✗ Model initialization failed: {e}[/bold red]")

    _show_model_info()


# Functions are exported and added to Litestar CLI by the plugin in server/core.py


# Main execution removed - CLI is handled by Litestar

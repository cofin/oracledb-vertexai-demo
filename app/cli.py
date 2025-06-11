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


__all__ = ["load_fixtures", "load_vectors", "recommend", "version_callback"]

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
            RecommendationService,
        )
        from app.services.account import (
            ChatConversationService,
            ResponseCacheService,
            SearchMetricsService,
            UserSessionService,
        )
        from app.services.vertex_ai import (
            OracleVectorSearchService,
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


# Functions are exported and added to Litestar CLI by the plugin in server/core.py


# Main execution removed - CLI is handled by Litestar

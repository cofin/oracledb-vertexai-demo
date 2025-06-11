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

    from app.domain.coffee.services import RecommendationService


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
        from app.domain.coffee.deps import (
            provide_product_service,
            provide_shop_service,
        )
        from app.domain.coffee.services import (
            RecommendationService,
        )
        from app.domain.coffee.services.account import (
            ChatConversationService,
            ResponseCacheService,
            SearchMetricsService,
            UserSessionService,
        )
        from app.domain.coffee.services.vertex_ai import (
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
                product_service=products_service,
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
        poi_template = dedent("""
        [{name}](https://www.google.com/maps/place/{latitude},{longitude}/@{latitude},{longitude},17z)
        {address}
        """)
        locations = [
            poi_template.format(
                name=poi.name,
                address=poi.address,
                latitude=poi.latitude,
                longitude=poi.longitude,
            )
            for poi in response.points_of_interest
        ]

        if panel:
            console.print(
                Panel(
                    Markdown("  \n".join(locations)) if locations else "No locations found.",
                    title="📍 Locations",
                    title_align="left",
                ),
            )
        else:
            console.print(NoPadding(Markdown("  \n".join(locations)) if locations else "No locations found."))


# Individual CLI functions - these will be added to Litestar's CLI by the plugin


def load_fixtures() -> None:
    """Load coffee demo fixture data."""

    async def _load_fixtures() -> None:
        from pathlib import Path

        from advanced_alchemy.utils.fixtures import open_fixture_async

        from app.config import alchemy
        from app.domain.coffee.deps import (
            provide_company_service,
            provide_inventory_service,
            provide_product_service,
            provide_shop_service,
        )

        async with alchemy.get_session() as db_session:
            companies_service = await anext(provide_company_service(db_session))
            products_service = await anext(provide_product_service(db_session))
            shops_service = await anext(provide_shop_service(db_session))
            inventory_service = await anext(provide_inventory_service(db_session))

            fixture_path = Path("app/db/fixtures")
            data = await open_fixture_async(fixtures_path=fixture_path, fixture_name="company")
            await companies_service.upsert_many(data, match_fields=["id"])

            # Load products
            products_data = await open_fixture_async(fixtures_path=fixture_path, fixture_name="product")
            await products_service.upsert_many(products_data, match_fields=["id"])

            # Load shops
            shops_data = await open_fixture_async(fixtures_path=fixture_path, fixture_name="shop")
            await shops_service.upsert_many(shops_data, match_fields=["id"])

            # Load inventory
            inventory_data = await open_fixture_async(fixtures_path=fixture_path, fixture_name="inventory")
            await inventory_service.upsert_many(inventory_data, match_fields=["shop_id", "product_id"])
            await db_session.commit()

        logger.info("Fixtures loaded successfully")

    anyio.run(_load_fixtures)


def load_vectors() -> None:
    """Generate and load vector embeddings for products."""

    async def _load_vectors() -> None:
        from app.config import alchemy
        from app.domain.coffee.deps import provide_product_service
        from app.domain.coffee.services.vertex_ai import VertexAIService

        async with alchemy.get_session() as db_session:
            products_service = await anext(provide_product_service(db_session))
            vertex_ai = VertexAIService()

            # Get all products
            products = await products_service.list()

            for product in products:
                # Generate embedding for product description
                embedding = await vertex_ai.create_embedding(product.description)

                # Update product with embedding
                await products_service.update({
                    "id": product.id,
                    "embedding": embedding,
                })

                logger.info(
                    "Generated embedding for product",
                    product_id=product.id,
                    product_name=product.name,
                )

        logger.info("Vector embeddings loaded successfully")

    anyio.run(_load_vectors)


# Functions are exported and added to Litestar CLI by the plugin in server/core.py


# Main execution removed - CLI is handled by Litestar

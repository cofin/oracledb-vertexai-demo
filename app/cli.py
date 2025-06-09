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

import multiprocessing
from textwrap import dedent
from typing import TYPE_CHECKING

import anyio
import click
import structlog
from click import Context, group, option, pass_context
from rich.prompt import Prompt

from app.__metadata__ import __version__

if TYPE_CHECKING:
    from typing import Any

    from asyncpg import Connection
    from rich.console import Console

    from app.domain.coffee.services import RecommendationService


__all__ = ["app", "version_callback"]

logger = structlog.get_logger()


def version_callback(ctx: Context, _: click.Parameter, value: bool) -> None:
    if value and not ctx.resilient_parsing:
        click.echo(f"{__version__}")
        ctx.exit()


@group(name="recommend")
def app_group() -> None:
    """Application Commands."""


@app_group.command(name="recommend", help="Find a coffee.")
def recommend() -> None:
    """Execute the recommendation engine from the CLI"""
    import anyio
    from rich import get_console

    async def _get_recommendations() -> None:
        from rich import get_console

        from app.config import alchemy
        from app.domain.coffee.dependencies import (
            provide_products_service,
            provide_shops_service,
        )
        from app.domain.coffee.services import (
            RecommendationService,
        )
        from app.domain.coffee.services.oracle_services import (
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
            shops_service = await anext(provide_shops_service(db_session))
            products_service = await anext(provide_products_service(db_session))

            # Initialize Vertex AI and Oracle services
            vertex_ai_service = VertexAIService()
            session_service = UserSessionService.Repo(session=db_session)
            conversation_service = ChatConversationService.Repo(session=db_session)
            cache_service = ResponseCacheService.Repo(session=db_session)
            metrics_service = SearchMetricsService.Repo(session=db_session)

            # Create wrapped services
            session_service_wrapped = UserSessionService(repository=session_service)
            conversation_service_wrapped = ChatConversationService(repository=conversation_service)
            cache_service_wrapped = ResponseCacheService(repository=cache_service)
            metrics_service_wrapped = SearchMetricsService(repository=metrics_service)

            vector_search_service = OracleVectorSearchService(
                product_service=products_service,
                vertex_ai_service=vertex_ai_service,
            )

            service = RecommendationService(
                vertex_ai_service=vertex_ai_service,
                vector_search_service=vector_search_service,
                products_service=products_service,
                shops_service=shops_service,
                session_service=session_service_wrapped,
                conversation_service=conversation_service_wrapped,
                cache_service=cache_service_wrapped,
                metrics_service=metrics_service_wrapped,
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
    service: "RecommendationService",
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
    service: "RecommendationService",
    message: str,
    panel: bool = True,
) -> None:
    """Execute the recommendation"""
    from rich import get_console
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.spinner import Spinner

    class NoPadding:
        def __init__(self, renderable: Any) -> None:
            self.renderable = renderable

        def __rich_console__(self, console: "Console", options: Any) -> Any:
            yield self.renderable

    console = get_console()
    from rich.panel import Panel

    panel_class = Panel if panel is True else NoPadding
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


@pass_context
@option(
    "--version",
    is_flag=True,
    callback=version_callback,
    expose_value=False,
    is_eager=True,
    help="Display the application version and exit.",
)
@option(
    "-v",
    "--verbose",
    help="Enable verbose output.",
    is_flag=True,
    default=False,
    type=bool,
)
@option(
    "-q",
    "--quiet",
    help="Suppress all output except errors.",
    is_flag=True,
    default=False,
    type=bool,
)
@group(
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 80},
    invoke_without_command=False,
    epilog="""
\b
For more information, visit: [github](https://github.com/cofin/oracledb-vertexai-demo)
    """,
)
def app(ctx: Context, verbose: bool, quiet: bool) -> None:
    """Oracle + VertexAI Coffee Demo CLI.

    For detailed information on a specific command, use:
    `oracledb-vertexai-demo database <COMMAND> --help`
    """
    ctx.obj = ctx.obj or {}
    ctx.obj.update(verbose=verbose, quiet=quiet)


@app.command(name="load-fixtures", help="Load fixture data into database")
def load_fixtures() -> None:
    """Load coffee demo fixture data."""

    async def _load_fixtures() -> None:
        from pathlib import Path

        import orjson

        from app.config import alchemy
        from app.db.models import Company, Inventory, Product, Shop
        from app.domain.coffee.dependencies import (
            provide_companies_service,
            provide_inventory_service,
            provide_products_service,
            provide_shops_service,
        )

        async with alchemy.get_session() as db_session:
            companies_service = await anext(provide_companies_service(db_session))
            products_service = await anext(provide_products_service(db_session))
            shops_service = await anext(provide_shops_service(db_session))
            inventory_service = await anext(provide_inventory_service(db_session))

            fixture_path = Path("app/db/fixtures")

            # Load companies
            with Path.open(fixture_path / "company.json", "rb") as f:
                company_data = orjson.loads(f.read())
                for company in company_data:
                    await companies_service.upsert(
                        Company(**company),
                        match_fields=["id"],
                    )

            # Load products
            with Path.open(fixture_path / "product.json", "rb") as f:
                products_data = orjson.loads(f.read())
                for product in products_data:
                    await products_service.upsert(
                        Product(**product),
                        match_fields=["id"],
                    )

            # Load shops
            with Path.open(fixture_path / "shop.json", "rb") as f:
                shops_data = orjson.loads(f.read())
                for shop in shops_data:
                    await shops_service.upsert(
                        Shop(**shop),
                        match_fields=["id"],
                    )

            # Load inventory
            with Path.open(fixture_path / "inventory.json", "rb") as f:
                inventory_data = orjson.loads(f.read())
                for item in inventory_data:
                    await inventory_service.upsert(
                        Inventory(**item),
                        match_fields=["shop_id", "product_id"],
                    )

        logger.info("Fixtures loaded successfully")

    anyio.run(_load_fixtures)


@app.command(name="load-vectors", help="Generate and load vector embeddings")
def load_vectors() -> None:
    """Generate and load vector embeddings for products."""

    async def _load_vectors() -> None:
        from app.config import alchemy
        from app.domain.coffee.dependencies import provide_products_service
        from app.domain.coffee.services.vertex_ai import VertexAIService

        async with alchemy.get_session() as db_session:
            products_service = await anext(provide_products_service(db_session))
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


app.add_command(app_group)

# Database commands are added via alembic
try:
    from app.lib.db import database_management_app

    app.add_command(database_management_app, name="database")
except ImportError:
    logger.warning("Database management commands not available")


async def wait_for_db(db_session: Connection, *, timeout: int = 10) -> None:
    """Wait for the database to be ready."""
    import asyncio

    async def _check() -> None:
        await db_session.fetchrow("SELECT 1")

    for _ in range(timeout * 2):
        try:
            await _check()
        except Exception:  # noqa: BLE001
            await asyncio.sleep(0.5)
        else:
            return

    msg = f"Database did not become ready within {timeout} seconds"
    raise TimeoutError(msg)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app()

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

from __future__ import annotations

from pathlib import Path

from advanced_alchemy.extensions.litestar.cli import database_group
from rich_click import group


@database_group.command(name="load-fixtures", help="Import base model seeding data.")
def load_fixtures() -> None:
    """Load default database fixtures for the application"""
    import anyio
    from rich import get_console

    console = get_console()

    console.rule("Loading fixtures")
    anyio.run(load_database_fixtures)
    console.rule("Fixtures loaded")


@database_group.command(name="load-vectors", help="Loading vector stores.")
def load_vectors() -> None:
    """Load default database vectors for the application"""
    from rich import get_console

    from app.domain.coffee.etl import generate_embeddings

    console = get_console()

    console.rule("Populating vector stores")
    generate_embeddings(False)
    console.rule("Vectors loaded")


@group(name="recommend")
def app_group() -> None:
    """Application Commands."""


@app_group.command(name="recommend", help="Find a coffee.")
def recommend() -> None:
    """Execute the recommendation engine from the CLI"""
    import anyio
    from rich import get_console

    from .utils import print_recommendations_header

    console = get_console()
    print_recommendations_header(console)
    anyio.run(get_recommendations)


async def get_recommendations() -> None:
    from langchain_community.vectorstores.oraclevs import OracleVS
    from rich import get_console

    from app.cli.utils import chat_session
    from app.config import alchemy, oracle
    from app.domain.coffee.dependencies import (
        provide_products_service,
        provide_shops_service,
    )
    from app.domain.coffee.services import (
        RecommendationService,
    )
    from app.domain.coffee.utils import get_embeddings_service
    from app.lib.settings import get_settings

    console = get_console()
    settings = get_settings()
    engine = alchemy.get_engine()
    async with alchemy.get_session() as db_session:
        shops_service = await anext(provide_shops_service(db_session))
        products_service = await anext(provide_products_service(db_session))
        with oracle.get_connection() as db_connection:
            embeddings = get_embeddings_service(model_type=settings.app.EMBEDDING_MODEL_TYPE)
            vector_store = OracleVS(
                client=db_connection,
                embedding_function=embeddings,
                table_name="PRODUCT_DESCRIPTION_VS",
                query="Where can I get a good coffee nearby?",
            )
            service = RecommendationService(
                vector_store=vector_store,
                products_service=products_service,
                shops_service=shops_service,
                history_meta={"user_id": "cli-0", "conversation_id": "cli-0"},
                system_context_message="""
        You are a helpful AI assistant specializing in coffee recommendations.
        Given a user's chat history and the latest user query and a list of matching coffees from a database, provide an engaging and informative response.
        If the user is asking about coffee recommendations and locations, provide the information and finish the response as concisely as possible.
        Your responses should always be returning in Markdown format.
        If the user is asking a general question or making a statement, respond appropriately without using the database.

        **Response:**
    """,
            )
            await chat_session(service=service, console=console)

    await engine.dispose()


async def load_database_fixtures() -> None:
    """Import/Synchronize Database Fixtures."""

    from advanced_alchemy.utils.fixtures import open_fixture_async
    from structlog import get_logger

    from app.config import alchemy
    from app.domain.coffee.services import CompanyService, InventoryService, ProductService, ShopService
    from app.lib.settings import get_settings

    settings = get_settings()
    logger = get_logger()
    fixtures_path = Path(settings.db.FIXTURE_PATH)
    async with CompanyService.new(config=alchemy) as service:
        fixture_data = await open_fixture_async(fixtures_path, "company")
        await service.upsert_many(match_fields=["name"], data=fixture_data, auto_commit=True)
        await logger.ainfo("loaded companies")
    async with ShopService.new(config=alchemy) as service:
        fixture_data = await open_fixture_async(fixtures_path, "shop")
        await service.upsert_many(match_fields=["name"], data=fixture_data, auto_commit=True)
        await logger.ainfo("loaded shops")
    async with ProductService.new(config=alchemy) as service:
        fixture_data = await open_fixture_async(fixtures_path, "product")
        await service.upsert_many(match_fields=["name"], data=fixture_data, auto_commit=True)
        await logger.ainfo("loaded products")
    async with InventoryService.new(config=alchemy) as service:
        fixture_data = await open_fixture_async(fixtures_path, "inventory")
        await service.upsert_many(match_fields=["shop_id", "product_id"], data=fixture_data, auto_commit=True)
        await logger.ainfo("loaded inventory")

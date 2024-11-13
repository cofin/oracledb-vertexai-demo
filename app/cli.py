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
from textwrap import dedent
from typing import TYPE_CHECKING, Any

from advanced_alchemy.extensions.litestar.cli import database_group
from rich.align import Align
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.spinner import Spinner
from rich_click import group

if TYPE_CHECKING:
    from langchain.schema import AIMessage, BaseMessage
    from prompt_toolkit import PromptSession
    from rich.console import Console, RenderableType

    from app.domain.coffee.services import RecommendationService


@group(name="recommend")
def app_group() -> None:
    """Application Commands."""


@app_group.command(name="recommend", help="Find a coffee.")
def recommend() -> None:
    """Execute the recommendation engine from the CLI"""
    import anyio
    from rich import get_console

    async def _get_recommendations() -> None:
        from langchain_community.vectorstores.oraclevs import OracleVS
        from rich import get_console

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
                    system_context_message=dedent("""
            You are a helpful AI assistant specializing in coffee recommendations.
            Given a user's chat history and the latest user query and a list of matching coffees from a database, provide an engaging and informative response.
            If the user is asking about coffee recommendations and locations, only provide the product information and finish the response as concisely as possible.
            Do not provide a list of details of the locations.  Only tell the customer how many locations nearby have the product.

            If the user is asking a general question or making a statement, respond appropriately without using the database.
            Your responses should be as concise as possible.  You should not have any "placeholder syntax" in your response. If you don't know, it should be omitted.
            Do not ask the user if you should list the stores.

            Your responses should always be returning in Markdown format.
            When providing locations, only provide responses that utilize the count of stores found that match the product selection.  The Locations will be provided separately by another component of the user interface.
        """),
                )
                await _chat_session(service=service, console=console)

        await engine.dispose()

    console = get_console()
    console.print(
        Panel(
            Align(
                renderable="[bold]  ☕   [/bold] [bold cyan]Personalized Coffee Recommendations[/bold cyan] [bold]   ☕  [/bold]\nWhat are you looking for today?  I can help you find the perfect coffee.",
                align="left",
            ),
            title="[blue bold]Cymbal Coffee Connoisseur[/blue bold]",
            title_align="left",
            style="green bold",
            expand=True,
        ),
    )
    console.print("")
    anyio.run(_get_recommendations)


async def _chat_session(
    service: RecommendationService,
    console: Console,
    panel: bool = True,
) -> None:
    """Coffee Chat Session"""
    from langchain.schema import HumanMessage
    from prompt_toolkit import PromptSession
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.history import FileHistory

    history_file = Path().home() / ".coffee-chat"
    history = FileHistory(str(history_file))
    session: PromptSession = PromptSession(history=history, erase_when_done=True)
    messages: list[BaseMessage] = []
    while True:
        text = await session.prompt_async("☕ > ", auto_suggest=AutoSuggestFromHistory())
        if not text:
            continue
        console.print(f"☕: {text}")
        if panel is False:
            console.print("")
            console.rule()
        messages.append(HumanMessage(content=text))
        console.print("")
        llm_message = await _print_response(
            service=service,
            console=console,
            message=text,  # pyright: ignore[reportPossiblyUnboundVariable]
            panel=panel,
        )
        if panel is False:
            console.print("")
            console.rule()
        messages.append(llm_message)
        console.rule(style="rule.dotted")


async def _print_response(
    service: RecommendationService,
    console: Console,
    message: str,
    panel: bool,
) -> AIMessage:
    """Stream the response"""
    from langchain.schema import AIMessage
    from rich.panel import Panel

    panel_class = Panel if panel is True else NoPadding
    with Live(Spinner("aesthetic"), refresh_per_second=15, console=console, transient=True):
        response = await service.get_recommendation(message)
        text = response["answer"]
        console.print_json(data=response)
        console.print(panel_class(Markdown(text), title="🤖 Cymbal AI", title_align="left"))
        poi_template = dedent("""
        [{name}](https://www.google.com/maps/place/{latitude},{longitude}/@{latitude},{longitude},17z)
        {address}
        """)
        locations = [
            poi_template.format(
                name=poi["name"],
                address=poi["address"],
                latitude=poi["latitude"],
                longitude=poi["longitude"],
            )
            for poi in response["points_of_interest"]
        ]
        if locations:
            console.print(
                panel_class(
                    Markdown("\n".join(locations)),
                    title="Nearby Locations",
                    title_align="left",
                ),
            )

    return AIMessage(content=text)


@database_group.command(name="load-fixtures", help="Import base model seeding data.")
def load_fixtures() -> None:
    """Load default database fixtures for the application"""
    import anyio
    from rich import get_console

    from app.db.utils import load_database_fixtures

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


class NoPadding(Padding):
    """Empty Panel"""

    def __init__(self, renderable: RenderableType, **kwargs: Any) -> None:
        """Create a Panel with no padding"""
        _ = kwargs
        super().__init__(renderable, pad=(0, 0, 0, 0))

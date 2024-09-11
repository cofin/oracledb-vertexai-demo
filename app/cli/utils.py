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

from langchain.schema import AIMessage, BaseMessage, HumanMessage
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from rich.align import Align
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.spinner import Spinner

if TYPE_CHECKING:
    from rich.console import Console, RenderableType

    from app.domain.coffee.services import RecommendationService


def print_recommendations_header(console: Console) -> None:
    """Print the header"""
    renderable = "[bold]  ☕   [/bold] [bold cyan]Personalized Coffee Recommendations[/bold cyan] [bold]   ☕  [/bold]\nWhat are you looking for today?  I can help you find the perfect coffee."
    console.print(
        Panel(
            Align(renderable=renderable, align="left"),
            title="[blue bold]Cymbal Coffee Connoisseur[/blue bold]",
            title_align="left",
            style="green bold",
            expand=True,
        ),
    )
    console.print("")


class NoPadding(Padding):
    """Empty Panel"""

    def __init__(self, renderable: RenderableType, **kwargs: Any) -> None:
        """Create a Panel with no padding"""
        _ = kwargs
        super().__init__(renderable, pad=(0, 0, 0, 0))


async def chat_session(
    service: RecommendationService,
    console: Console,
    panel: bool = True,
) -> None:
    """Coffee Chat Session"""
    history_file = Path().home() / ".coffee-chat"
    history = FileHistory(str(history_file))
    session: PromptSession = PromptSession(history=history, erase_when_done=True)
    messages: list[BaseMessage] = []
    message_counter = 0
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
        llm_message = await print_response(
            service=service,
            console=console,
            message=text,  # pyright: ignore[reportPossiblyUnboundVariable]
            panel=panel,
        )
        if panel is False:
            console.print("")
            console.rule()
        messages.append(llm_message)
        console.print("")
        message_counter += 1


async def print_response(
    service: RecommendationService,
    console: Console,
    message: str,
    panel: bool,
) -> AIMessage:
    """Stream the response"""
    panel_class = Panel if panel is True else NoPadding
    with Live(Spinner("aesthetic"), refresh_per_second=15, console=console, transient=True):
        response = await service.ask_question(message)
        text = response["answer"]
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

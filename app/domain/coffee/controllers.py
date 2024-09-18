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

from typing import Annotated

from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import Runnable
from litestar import Controller, WebSocket, get, post
from litestar.channels import ChannelsPlugin
from litestar.datastructures import State
from litestar.di import Provide
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import File, Template
from litestar_vite.inertia import InertiaRequest

from app import config
from app.domain.coffee.dependencies import (
    provide_embeddings_service,
    provide_product_description_vector_store,
    provide_products_service,
    provide_recommendation_service,
    provide_retrieval_chain,
    provide_shops_service,
)
from app.domain.coffee.schemas import CoffeeChatMessage, CoffeeChatReply
from app.domain.coffee.services import ProductService, RecommendationService, ShopService
from app.lib.settings import get_settings


class CoffeeChatController(Controller):
    @get(path="/", name="ocw.show")
    async def show_ocw(self) -> Template:
        """Serve site root."""
        settings = get_settings()
        return Template(template_name="ocw.html.j2", context={"google_maps_api_key": settings.app.GOOGLE_API_KEY})

    @post(path="/", name="ocw.get")
    async def get_ocw(
        self,
        data: Annotated[CoffeeChatMessage, Body(title="Discover Coffee", media_type=RequestEncodingType.URL_ENCODED)],
        recommendation_service: RecommendationService,
    ) -> Template:
        """Serve site root."""
        settings = get_settings()
        reply = await recommendation_service.ask_question(data.message.lower())
        return Template(
            template_name="ocw.html.j2",
            context={
                "google_maps_api_key": settings.app.GOOGLE_API_KEY,
                "answer": reply["answer"],
                "points_of_interest": reply["points_of_interest"],
            },
        )

    @get(component="coffee/simple-chat", name="simple-chat.show", path="/simple-chat/")
    async def simple_chat_show(self) -> dict:
        return {}

    @post(component="coffee/simple-chat", name="simple-chat.send", path="/simple-chat/")
    async def simple_chat_send(
        self,
        data: CoffeeChatMessage,
        recommendation_service: RecommendationService,
    ) -> CoffeeChatReply:
        return await recommendation_service.ask_question(data.message.lower())

    @get(path="/favicon.ico", name="favicon", exclude_from_auth=True, sync_to_thread=False, include_in_schema=False)
    def favicon(self) -> File:
        """Serve site root."""
        return File(path=f"{config.vite.public_dir}/favicon.ico")

    dependencies = {
        "embeddings": Provide(provide_embeddings_service),
        "vector_store": Provide(provide_product_description_vector_store),
        "retrieval_chain": Provide(provide_retrieval_chain),
        "products_service": Provide(provide_products_service),
        "shops_service": Provide(provide_shops_service),
        "recommendation_service": Provide(provide_recommendation_service),
    }
    signature_namespace = {"Request": InertiaRequest}
    signature_types = [
        Runnable,
        ChannelsPlugin,
        WebSocket,
        State,
        Embeddings,
        OracleVS,
        ProductService,
        ShopService,
        CoffeeChatReply,
        RecommendationService,
        CoffeeChatMessage,
        Body,
        RequestEncodingType,
    ]

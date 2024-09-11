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

from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import Runnable
from litestar import Controller, WebSocket, get, post
from litestar.channels import ChannelsPlugin
from litestar.datastructures import State
from litestar.di import Provide
from litestar_vite.inertia import InertiaRequest

from app.domain.coffee.dependencies import (
    provide_embeddings_service,
    provide_product_description_vector_store,
    provide_products_service,
    provide_recommendation_service,
    provide_retrieval_chain,
    provide_shops_service,
)
from app.domain.coffee.services import CoffeeChatReply, ProductService, RecommendationService, ShopService
from app.lib.schema import CamelizedBaseStruct


class CoffeeChatMessage(CamelizedBaseStruct):
    message: str


class CoffeeChatController(Controller):
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
    ]

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

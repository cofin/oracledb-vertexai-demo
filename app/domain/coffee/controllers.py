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

from typing import TYPE_CHECKING, Annotated

from litestar import Controller, get, post
from litestar.di import Provide
from litestar.response import File, Template

from app import config
from app.domain.coffee.dependencies import (
    provide_chat_conversation_service,
    provide_oracle_vector_search_service,
    provide_products_service,
    provide_recommendation_service,
    provide_response_cache_service,
    provide_search_metrics_service,
    provide_shops_service,
    provide_user_session_service,
    provide_vertex_ai_service,
)
from app.lib.settings import get_settings

if TYPE_CHECKING:
    from litestar.enums import RequestEncodingType
    from litestar.params import Body

    from app.domain.coffee.schemas import CoffeeChatMessage
    from app.domain.coffee.services.recommendation import RecommendationService


class CoffeeChatController(Controller):
    dependencies = {
        "vertex_ai_service": Provide(provide_vertex_ai_service),
        "vector_search_service": Provide(provide_oracle_vector_search_service),
        "products_service": Provide(provide_products_service),
        "shops_service": Provide(provide_shops_service),
        "session_service": Provide(provide_user_session_service),
        "conversation_service": Provide(provide_chat_conversation_service),
        "cache_service": Provide(provide_response_cache_service),
        "metrics_service": Provide(provide_search_metrics_service),
        "recommendation_service": Provide(provide_recommendation_service),
    }

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
        reply = await recommendation_service.get_recommendation(data.message)
        return Template(
            template_name="ocw.html.j2",
            context={
                "google_maps_api_key": settings.app.GOOGLE_API_KEY,
                "answer": reply.answer,
                "points_of_interest": [poi.__dict__ for poi in reply.points_of_interest],
            },
        )

    @get(path="/favicon.ico", name="favicon", exclude_from_auth=True, sync_to_thread=False, include_in_schema=False)
    def favicon(self) -> File:
        """Serve site root."""
        return File(path=f"{config.vite.public_dir}/favicon.ico")

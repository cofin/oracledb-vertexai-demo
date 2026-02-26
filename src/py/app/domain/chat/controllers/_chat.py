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

import re
import uuid

from litestar import Controller, post
from litestar.connection import Request
from litestar.exceptions import ValidationException

from app import schemas
from app.domain.chat.services import ADKRunner
from app.domain.system.services import CacheService
from app.lib.di import Inject


class CoffeeChatController(Controller):
    """Coffee chat API controller for React clients."""

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate and sanitize user message input."""
        message = re.sub(r"<[^>]+>", "", message)
        max_length = 500
        if len(message) > max_length:
            message = message[:max_length]
        message = message.replace("\x00", "").strip()

        if not message:
            raise ValidationException(detail="Message cannot be empty")

        return message

    @staticmethod
    def validate_persona(persona: str) -> str:
        """Validate persona input."""
        if persona not in {"novice", "enthusiast", "expert", "barista"}:
            return "enthusiast"
        return persona

    @post(path="/api/chat", name="chat.api.send")
    async def send_chat_message(
        self,
        data: schemas.CoffeeChatMessage,
        adk_runner: Inject[ADKRunner],
        cache_service: Inject[CacheService],
        request: Request,
    ) -> schemas.CoffeeChatReply:
        """Handle chat submission for SPA clients."""
        clean_message = self.validate_message(data.message)
        validated_persona = self.validate_persona(data.persona)
        session_id = request.headers.get("x-session-id", str(uuid.uuid4()))

        result = await adk_runner.process_request(
            query=clean_message,
            user_id="web_user",
            session_id=session_id,
            persona=validated_persona,
            cache_service=cache_service,
        )

        return schemas.CoffeeChatReply(
            message=clean_message,
            messages=[
                schemas.ChatMessage(message=clean_message, source="human"),
                schemas.ChatMessage(message=result.get("answer", ""), source="ai"),
            ],
            answer=result.get("answer", ""),
            query_id=str(uuid.uuid4()),
            search_metrics={
                "response_time_ms": result.get("response_time_ms", 0),
                "agent_processing_ms": result.get("agent_processing_ms", 0),
                "session_id": result.get("session_id", session_id),
                "intent_details": result.get("intent_details", {}),
                "search_details": result.get("search_details", {}),
                "store_details": result.get("store_details", {}),
                "products_found": result.get("products_found", []),
                "stores_found": result.get("stores_found", []),
            },
            from_cache=bool(result.get("from_cache", False)),
            embedding_cache_hit=bool(result.get("embedding_cache_hit", False)),
            intent_detected=result.get("intent_detected")
            or result.get("intent_details", {}).get("intent", "GENERAL_CONVERSATION"),
        )

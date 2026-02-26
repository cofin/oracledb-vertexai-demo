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
import secrets
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated, Any

import structlog
from litestar import Controller, get, post
from litestar.enums import RequestEncodingType
from litestar.exceptions import ValidationException
from litestar.params import Body
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.response import Stream

from app import schemas
from app.domain.chat.services import ADKRunner
from app.domain.system.services import CacheService, MetricsService
from app.lib.di import Inject, query_id_var
from app.utils.serialization import to_json

logger = structlog.get_logger()


class CoffeeChatController(Controller):
    """Coffee Chat Controller with ADK-based agent system."""

    @staticmethod
    def generate_csp_nonce() -> str:
        """Generate a  CSP nonce."""
        return secrets.token_urlsafe(16)

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

    @get(path="/chat", name="coffee_chat.show")
    async def show_coffee_chat(self) -> HTMXTemplate:
        """Serve site root with CSP nonce."""
        return HTMXTemplate(
            template_name="coffee_chat.html",
            context={"csp_nonce": self.generate_csp_nonce()},
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=()",
            },
        )

    @post(path="/chat", name="coffee_chat.get")
    async def handle_coffee_chat(
        self,
        data: Annotated[
            schemas.CoffeeChatMessage, Body(title="Discover Coffee", media_type=RequestEncodingType.URL_ENCODED)
        ],
        cache_service: Inject[CacheService],
        request: HTMXRequest,
    ) -> HTMXTemplate:
        """Handle chat submission with optimistic UI pattern."""
        csp_nonce = self.generate_csp_nonce()
        clean_message = self.validate_message(data.message)
        validated_persona = self.validate_persona(data.persona)
        query_id = str(uuid.uuid4())

        session_id = request.session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session["session_id"] = session_id

        query_state = {
            "query": clean_message,
            "session_id": session_id,
            "persona": validated_persona,
            "user_id": "web_user",
            "timestamp": time.time(),
        }
        await cache_service.set_query_state(
            query_id=query_id,
            state=query_state,
            ttl_minutes=5,
        )

        return HTMXTemplate(
            template_name="partials/chat_streaming.html",
            context={
                "user_message": clean_message,
                "query_id": query_id,
                "persona": validated_persona,
                "csp_nonce": csp_nonce,
            },
            trigger_event="chat:user-message-added",
            params={"query_id": query_id},
            after="settle",
        )

    async def _stream_cached_response(
        self,
        cached: Any,
        query_id: str,
        cache_service: CacheService,
    ) -> AsyncGenerator[str, None]:
        """Stream cached response as SSE events."""
        logger.info("Streaming cached response", query_id=query_id)
        answer_text = cached.response_data.get("answer", "")
        yield f"event: message\ndata: {to_json({'html': answer_text}, as_bytes=False)}\n\n"
        yield f"event: complete\ndata: {to_json({'done': True, 'from_cache': True}, as_bytes=False)}\n\n"
        await cache_service.delete_query_state(query_id)

    async def _stream_adk_events(
        self,
        adk_runner: ADKRunner,
        query: str,
        user_id: str,
        session_id: str,
        persona: str,
        cache_service: CacheService,
    ) -> AsyncGenerator[tuple[str, dict], None]:
        """Stream ADK events and yield SSE-formatted strings."""
        accumulated_text = []
        intent_details = {}
        search_details = {}
        store_details = {}
        embedding_cache_hit = False

        events = adk_runner.stream_request(
            query=query,
            user_id=user_id,
            session_id=session_id,
            persona=persona,
            cache_service=cache_service,
        )

        async for chunk in events:
            chunk_type = chunk.get("type")

            if chunk_type == "text":
                text = chunk.get("text", "")
                accumulated_text.append(text)
                yield (
                    f"event: chunk\ndata: {to_json({'text': text}, as_bytes=False)}\n\n",
                    {
                        "text": accumulated_text,
                    },
                )

            elif chunk_type == "intent":
                intent_details = chunk.get("data", {})
                yield (
                    f"event: metadata\ndata: {to_json({'type': 'intent', 'data': intent_details}, as_bytes=False)}\n\n",
                    {
                        "intent": intent_details,
                    },
                )

            elif chunk_type == "products":
                search_details = chunk.get("data", {})
                yield (
                    f"event: metadata\ndata: {to_json({'type': 'products', 'data': search_details}, as_bytes=False)}\n\n",
                    {
                        "products": search_details,
                    },
                )

            elif chunk_type == "stores":
                store_details = chunk.get("data", {})
                yield (
                    f"event: metadata\ndata: {to_json({'type': 'stores', 'data': store_details}, as_bytes=False)}\n\n",
                    {
                        "stores": store_details,
                    },
                )

            elif chunk_type == "cache_hit":
                embedding_cache_hit = True
                yield "", {"embedding_cache_hit": True}

        yield (
            "",
            {
                "accumulated_text": accumulated_text,
                "intent_details": intent_details,
                "search_details": search_details,
                "store_details": store_details,
                "embedding_cache_hit": embedding_cache_hit,
            },
        )

    @get(path="/chat/stream/{query_id:str}", name="chat.stream")
    async def stream_response(  # noqa: C901, PLR0915
        self,
        query_id: str,
        adk_runner: Inject[ADKRunner],
        cache_service: Inject[CacheService],
        metrics_service: Inject[MetricsService],
    ) -> Stream:
        """Stream AI response using Server-Sent Events."""
        if not re.match(r"^[a-fA-F0-9\-]+", query_id):

            async def error_generate() -> AsyncGenerator[str, None]:
                yield 'event: error\ndata: {"error": "Invalid query ID"}\n\n'

            return Stream(error_generate(), media_type="text/event-stream")

        async def generate() -> AsyncGenerator[str, None]:
            try:
                query_state = await cache_service.get_query_state(query_id)
                if not query_state:
                    yield 'event: error\ndata: {"error": "Query not found or expired"}\n\n'
                    return

                query = query_state["query"]
                session_id = query_state["session_id"]
                persona = query_state["persona"]
                user_id = query_state["user_id"]

                cache_key = f"{query}|{persona}"
                cached = await cache_service.get_cached_response(cache_key=cache_key)

                if cached:
                    async for sse_event in self._stream_cached_response(cached, query_id, cache_service):
                        yield sse_event
                    return

                logger.info("Streaming from ADK", query_id=query_id)
                start_time = time.time()
                token = query_id_var.set(query_id)

                try:
                    accumulated_text: list[str] = []
                    intent_details: dict[str, Any] = {}
                    search_details: dict[str, Any] = {}
                    store_details: dict[str, Any] = {}
                    embedding_cache_hit: bool = False

                    async for sse_event, metadata in self._stream_adk_events(
                        adk_runner, query, user_id, session_id, persona, cache_service
                    ):
                        if sse_event:
                            yield sse_event
                        accumulated_text = metadata.get("text") or accumulated_text
                        intent_details = metadata.get("intent") or intent_details
                        if "products" in metadata:
                            search_details = metadata["products"]
                        if "stores" in metadata:
                            store_details = metadata["stores"]
                        embedding_cache_hit = metadata.get("embedding_cache_hit", embedding_cache_hit)
                        if "accumulated_text" in metadata:
                            accumulated_text = metadata["accumulated_text"]
                            intent_details = metadata["intent_details"]
                            search_details = metadata["search_details"]
                            store_details = metadata.get("store_details", {})

                    total_time_ms = round((time.time() - start_time) * 1000, 2)
                    yield f"event: complete\ndata: {to_json({'done': True, 'query_id': query_id, 'response_time_ms': total_time_ms, 'embedding_cache_hit': embedding_cache_hit}, as_bytes=False)}\n\n"

                    products_found = search_details.get("products", []) if search_details else []
                    await metrics_service.record_search(
                        schemas.SearchMetricsCreate(
                            query_id=query_id,
                            user_id=session_id,
                            search_time_ms=total_time_ms,
                            embedding_time_ms=search_details.get("embedding_ms", 0) if search_details else 0,
                            oracle_time_ms=search_details.get("search_ms", 0) if search_details else 0,
                            ai_time_ms=total_time_ms,
                            intent_time_ms=intent_details.get("timing_ms", 0) if intent_details else 0,
                            similarity_score=0.0,
                            result_count=len(products_found),
                        ),
                    )

                    final_answer = " ".join(accumulated_text)
                    if final_answer:
                        await cache_service.set_cached_response(
                            cache_key=cache_key,
                            response_data={
                                "answer": final_answer,
                                "response_time_ms": total_time_ms,
                                "intent_details": intent_details,
                                "search_details": search_details,
                                "store_details": store_details,
                                "products_found": products_found,
                                "embedding_cache_hit": embedding_cache_hit,
                            },
                            ttl_minutes=5,
                        )
                finally:
                    query_id_var.reset(token)
                    await cache_service.delete_query_state(query_id)

            except Exception as e:
                logger.exception("Stream error", query_id=query_id, error=str(e))
                yield f"event: error\ndata: {to_json({'error': 'Service error'}, as_bytes=False)}\n\n"

        return Stream(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Content-Type-Options": "nosniff",
            },
        )


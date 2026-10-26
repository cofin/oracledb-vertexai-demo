# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""OpenAI-compatible Vertex AI gateway controller for Oracle APEX 26.1 Generative AI Services."""

import inspect
import secrets
import time
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from uuid import uuid4

from dishka import AsyncContainer
from google.auth.exceptions import GoogleAuthError
from litestar import Request, get, post
from litestar.exceptions import NotAuthorizedException, ValidationException
from litestar.response import Stream
from litestar.status_codes import HTTP_200_OK
from litestar_security import AuthenticationPolicy, PublicController, exclude

from app.domain.ai.runtime import AgentEvent, Content, GeminiModelClient, Part, Usage
from app.domain.products.schemas import (
    OpenAIChatChoice,
    OpenAIChatCompletionChunk,
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIChatMessage,
    OpenAIChatResponseMessage,
    OpenAIChatStreamChoice,
    OpenAIChatStreamDelta,
    OpenAIModelCard,
    OpenAIModelList,
    OpenAIUsage,
)
from app.lib.di import Inject
from app.lib.exceptions import AIServiceUnconfigured, is_credential_error, is_expected_service_unavailable
from app.lib.settings import Settings
from app.utils.serialization import encode_json

__all__ = ("ApexAIController",)

_APEX_AI_TAG = "APEX AI Gateway"
_DEFAULT_CHAT_MODEL = "gemini-3.8-flash"
_UNCONFIGURED_MESSAGE = "Vertex AI service is not configured."


class ApexAIController(PublicController):
    """OpenAI-compatible ``/api/apex/ai/v1`` gateway backed by ``GeminiModelClient``."""

    path = "/api/apex/ai/v1"
    tags = [_APEX_AI_TAG]
    auth: ClassVar[AuthenticationPolicy] = exclude()

    @get("/models", operation_id="ApexAIListModels", name="apex_ai:models", summary="OpenAI-Compatible Model List")
    async def list_models(self, request: Request[Any, Any, Any], settings: Inject[Settings]) -> OpenAIModelList:
        """Return OpenAI model cards for APEX Generative AI Service connection tests."""
        self._verify_bearer_auth(request, settings)
        chat_model = (settings.ai.chat_model or "").strip().removeprefix("google/").strip() or _DEFAULT_CHAT_MODEL
        model_ids = tuple(dict.fromkeys((chat_model, f"google/{chat_model}")))
        return OpenAIModelList(data=[OpenAIModelCard(id=model_id) for model_id in model_ids])

    @post(
        "/chat/completions",
        operation_id="ApexAIChatCompletions",
        name="apex_ai:chat_completions",
        summary="OpenAI-Compatible Chat Completions",
        status_code=HTTP_200_OK,
        opt={"exclude_from_csrf": True},
    )
    async def chat_completions(
        self,
        request: Request[Any, Any, Any],
        data: OpenAIChatCompletionRequest,
        container: Inject[AsyncContainer],
        settings: Inject[Settings],
    ) -> OpenAIChatCompletionResponse | Stream:
        """Translate OpenAI Chat Completions requests to ``GeminiModelClient`` in JSON or SSE mode."""
        self._verify_bearer_auth(request, settings)
        system_instruction, contents = self._translate_messages(data.messages)

        try:
            model_client = await container.get(GeminiModelClient)
        except Exception as exc:
            self._raise_if_service_unavailable(exc)
            raise

        configured_default = (settings.ai.chat_model or "").strip() or _DEFAULT_CHAT_MODEL
        requested_model = (data.model or configured_default).strip() or configured_default
        gemini_model = requested_model.removeprefix("google/").strip() or _DEFAULT_CHAT_MODEL

        completion_id = f"chatcmpl-{uuid4().hex[:24]}"
        created_ts = int(time.time())

        if data.stream:
            return await self._stream_completion(
                model_client=model_client,
                contents=contents,
                system_instruction=system_instruction,
                gemini_model=gemini_model,
                requested_model=requested_model,
                temperature=data.temperature,
                completion_id=completion_id,
                created_ts=created_ts,
            )

        return await self._collect_completion(
            model_client=model_client,
            contents=contents,
            system_instruction=system_instruction,
            gemini_model=gemini_model,
            requested_model=requested_model,
            temperature=data.temperature,
            completion_id=completion_id,
            created_ts=created_ts,
        )

    @staticmethod
    def _verify_bearer_auth(request: Request[Any, Any, Any], settings: Settings) -> None:
        """Enforce constant-time Bearer token authentication when ``APEX_GATEWAY_API_KEY`` is configured."""
        expected_key = (settings.app.APEX_GATEWAY_API_KEY or "").strip()
        if not expected_key:
            return

        auth_header = (request.headers.get("authorization") or "").strip()
        scheme, sep, raw_token = auth_header.partition(" ")
        token = raw_token.strip()
        if (
            not sep
            or scheme.lower() != "bearer"
            or not token
            or not secrets.compare_digest(token.encode("utf-8"), expected_key.encode("utf-8"))
        ):
            raise NotAuthorizedException(detail="Invalid or missing Bearer token")

    @staticmethod
    def _translate_messages(messages: list[OpenAIChatMessage]) -> tuple[str | None, list[Content]]:
        """Extract system instructions and convert user/assistant turns into ``Content`` items."""
        if not messages:
            raise ValidationException(detail="At least one user or assistant message is required")

        system_parts: list[str] = []
        contents: list[Content] = []
        for message in messages:
            text = message.text_content()
            stripped = text.strip()
            if not stripped:
                continue
            if message.role in {"system", "developer"}:
                system_parts.append(stripped)
            elif message.role == "user":
                contents.append(Content(role="user", parts=[Part(text=text)]))
            elif message.role == "assistant":
                contents.append(Content(role="model", parts=[Part(text=text)]))

        if not contents:
            raise ValidationException(detail="At least one user or assistant message is required")

        system_instruction = "\n\n".join(system_parts) if system_parts else None
        return system_instruction, contents

    @classmethod
    async def _collect_completion(
        cls,
        *,
        model_client: GeminiModelClient,
        contents: list[Content],
        system_instruction: str | None,
        gemini_model: str,
        requested_model: str,
        temperature: float,
        completion_id: str,
        created_ts: int,
    ) -> OpenAIChatCompletionResponse:
        """Aggregate streaming Gemini events into a single OpenAI Chat Completions JSON response."""
        text_parts: list[str] = []
        latest_usage: Usage | None = None
        try:
            async for event in model_client.generate_stream(
                contents, system_instruction=system_instruction, model=gemini_model, temperature=temperature
            ):
                piece = event.text()
                if piece:
                    text_parts.append(piece)
                if event.usage is not None:
                    latest_usage = event.usage
        except Exception as exc:
            cls._raise_if_service_unavailable(exc)
            raise

        openai_usage = (
            OpenAIUsage(
                prompt_tokens=latest_usage.prompt_tokens,
                completion_tokens=latest_usage.output_tokens,
                total_tokens=latest_usage.total_tokens,
            )
            if latest_usage is not None
            else OpenAIUsage()
        )
        return OpenAIChatCompletionResponse(
            id=completion_id,
            created=created_ts,
            model=requested_model,
            choices=[
                OpenAIChatChoice(
                    index=0, message=OpenAIChatResponseMessage(content="".join(text_parts)), finish_reason="stop"
                )
            ],
            usage=openai_usage,
        )

    @classmethod
    async def _stream_completion(
        cls,
        *,
        model_client: GeminiModelClient,
        contents: list[Content],
        system_instruction: str | None,
        gemini_model: str,
        requested_model: str,
        temperature: float,
        completion_id: str,
        created_ts: int,
    ) -> Stream:
        """Pre-fetch the first model event to report 503 before returning a ``text/event-stream`` response."""
        stream_iter = aiter(
            model_client.generate_stream(
                contents, system_instruction=system_instruction, model=gemini_model, temperature=temperature
            )
        )
        try:
            first_event: AgentEvent | None = await anext(stream_iter)
        except StopAsyncIteration:
            first_event = None
        except Exception as exc:
            await cls._aclose_iterator(stream_iter)
            cls._raise_if_service_unavailable(exc)
            raise

        return Stream(
            cls._build_sse_iterator(
                first_event=first_event,
                stream_iter=stream_iter,
                completion_id=completion_id,
                created_ts=created_ts,
                requested_model=requested_model,
            ),
            media_type="text/event-stream",
            headers={
                "Content-Type": "text/event-stream; charset=utf-8",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @classmethod
    async def _build_sse_iterator(
        cls,
        *,
        first_event: AgentEvent | None,
        stream_iter: AsyncIterator[AgentEvent],
        completion_id: str,
        created_ts: int,
        requested_model: str,
    ) -> AsyncIterator[str]:
        """Yield OpenAI Chat Completions SSE chunk frames terminated by ``data: [DONE]``."""
        try:
            role_chunk = OpenAIChatCompletionChunk(
                id=completion_id,
                created=created_ts,
                model=requested_model,
                choices=[
                    OpenAIChatStreamChoice(index=0, delta=OpenAIChatStreamDelta(role="assistant"), finish_reason=None)
                ],
            )
            yield f"data: {encode_json(role_chunk)}\n\n"

            if first_event is not None:
                first_text = first_event.text()
                if first_text:
                    first_chunk = OpenAIChatCompletionChunk(
                        id=completion_id,
                        created=created_ts,
                        model=requested_model,
                        choices=[
                            OpenAIChatStreamChoice(
                                index=0, delta=OpenAIChatStreamDelta(content=first_text), finish_reason=None
                            )
                        ],
                    )
                    yield f"data: {encode_json(first_chunk)}\n\n"

                async for event in stream_iter:
                    piece = event.text()
                    if piece:
                        content_chunk = OpenAIChatCompletionChunk(
                            id=completion_id,
                            created=created_ts,
                            model=requested_model,
                            choices=[
                                OpenAIChatStreamChoice(
                                    index=0, delta=OpenAIChatStreamDelta(content=piece), finish_reason=None
                                )
                            ],
                        )
                        yield f"data: {encode_json(content_chunk)}\n\n"

            stop_chunk = OpenAIChatCompletionChunk(
                id=completion_id,
                created=created_ts,
                model=requested_model,
                choices=[OpenAIChatStreamChoice(index=0, delta=OpenAIChatStreamDelta(), finish_reason="stop")],
            )
            yield f"data: {encode_json(stop_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            await cls._aclose_iterator(stream_iter)

    @staticmethod
    async def _aclose_iterator(stream_iter: AsyncIterator[AgentEvent]) -> None:
        """Close an async generator iterator when it exposes an ``aclose`` coroutine method."""
        aclose = getattr(stream_iter, "aclose", None)
        if callable(aclose):
            maybe_coro = aclose()
            if inspect.isawaitable(maybe_coro):
                await maybe_coro

    @staticmethod
    def _raise_if_service_unavailable(exc: Exception) -> None:
        """Convert expected Google credential and Vertex unavailability errors into HTTP 503."""
        if isinstance(exc, AIServiceUnconfigured):
            raise exc
        if isinstance(exc, GoogleAuthError) or is_credential_error(exc) or is_expected_service_unavailable(exc):
            raise AIServiceUnconfigured(_UNCONFIGURED_MESSAGE) from exc

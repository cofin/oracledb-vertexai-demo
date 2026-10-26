# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the OpenAI-compatible APEX Vertex AI gateway controller and wire schemas."""

from __future__ import annotations

import gc
import inspect
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest
from dishka import Provider, Scope, make_async_container
from google.auth.exceptions import DefaultCredentialsError
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.openapi import OpenAPIConfig
from litestar.plugins.problem_details import ProblemDetailsConfig, ProblemDetailsPlugin
from litestar.testing import AsyncTestClient
from litestar_security import SecurityPlugin
from tools.oracle.apex_catalog import build_apex_catalog

from app.domain.ai.runtime._model import GeminiModelClient
from app.domain.ai.runtime._types import AgentEvent, Content, Part, Usage
from app.domain.products.controllers import ApexAIController, ApexController
from app.domain.products.controllers import _apex_ai as apex_ai_controller_module
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
    OpenAITextContentPart,
    OpenAIUsage,
)
from app.ioc._ai import AIProvider
from app.lib.di import LitestarProvider, LitestarRouter, setup_dishka
from app.lib.exceptions import AIServiceUnconfigured, ai_service_unconfigured_handler
from app.lib.schema import FrozenBaseStruct
from app.lib.security import build_security_config
from app.lib.settings import AISettings, AppSettings, Settings
from app.utils.serialization import decode_json, encode_json

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Sequence

pytestmark = pytest.mark.anyio

TEST_GATEWAY_TOKEN = "apex-gateway-shared-secret"
TEST_CSRF_SECRET = "cymbal-coffee-csrf-test-secret-32b"


class _FakeGeminiModelClient:
    """Deterministic GeminiModelClient double recording generate_stream invocations."""

    __slots__ = ("_error", "_events", "calls", "closed_streams")

    def __init__(self, events: Sequence[AgentEvent] = (), *, error: Exception | None = None) -> None:
        self._events = tuple(events)
        self._error = error
        self.calls: list[dict[str, Any]] = []
        self.closed_streams = 0

    async def generate_stream(
        self,
        contents: Sequence[Content],
        *,
        tools: Sequence[Any] | None = None,
        system_instruction: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[AgentEvent]:
        """Record call parameters and yield configured AgentEvent chunks or raise configured error."""
        self.calls.append({
            "contents": list(contents),
            "tools": tools,
            "system_instruction": system_instruction,
            "model": model,
            "temperature": temperature,
        })
        try:
            if self._error is not None:
                raise self._error
            for event in self._events:
                yield event
        finally:
            self.closed_streams += 1


def _event(text: str, *, usage: Usage | None = None) -> AgentEvent:
    """Construct a streaming AgentEvent carrying model text and optional usage metadata."""
    return AgentEvent(
        session_id="",
        invocation_id="",
        content=Content(role="model", parts=[Part(text=text)]) if text else None,
        partial=True,
        usage=usage,
    )


def _settings(*, gateway_api_key: str | None = None, chat_model: str = "gemini-3.8-flash") -> Settings:
    """Construct isolated Settings for gateway unit tests."""
    base = Settings()
    return replace(
        base,
        app=replace(base.app, DEBUG=False, APEX_GATEWAY_API_KEY=gateway_api_key),
        ai=replace(base.ai, chat_model=chat_model),
    )


@asynccontextmanager
async def _gateway_client(
    fake_client: _FakeGeminiModelClient,
    *,
    gateway_api_key: str | None = None,
    chat_model: str = "gemini-3.8-flash",
    enable_csrf: bool = False,
) -> AsyncGenerator[AsyncTestClient[Litestar], None]:
    """Yield an AsyncTestClient wired with Dishka providers for ApexAIController."""
    settings = _settings(gateway_api_key=gateway_api_key, chat_model=chat_model)
    provider = Provider(scope=Scope.APP)
    provider.provide(lambda: fake_client, provides=GeminiModelClient)
    provider.provide(lambda: settings, provides=Settings)
    provider.provide(lambda: settings.app, provides=AppSettings)
    provider.provide(lambda: settings.ai, provides=AISettings)
    container = make_async_container(LitestarProvider(), provider)

    csrf_cfg = CSRFConfig(secret=TEST_CSRF_SECRET) if enable_csrf else None
    app = Litestar(
        route_handlers=[LitestarRouter(path="", route_handlers=[ApexAIController])],
        csrf_config=csrf_cfg,
        exception_handlers={AIServiceUnconfigured: ai_service_unconfigured_handler},
        openapi_config=OpenAPIConfig(title="Gateway Test API", version="0.3.1"),
        plugins=[
            ProblemDetailsPlugin(config=ProblemDetailsConfig(enable_for_all_http_exceptions=True)),
            SecurityPlugin(config=replace(build_security_config(settings), exclude=None)),
        ],
    )
    setup_dishka(container, app)
    try:
        async with AsyncTestClient(app=app) as client:
            yield client
    finally:
        await container.close()


@asynccontextmanager
async def _unconfigured_ai_provider_client(
    *, gateway_api_key: str | None = TEST_GATEWAY_TOKEN
) -> AsyncGenerator[AsyncTestClient[Litestar], None]:
    """Yield an AsyncTestClient wired with AIProvider's GenAI factories and unconfigured AISettings."""
    base = _settings(gateway_api_key=gateway_api_key)
    settings = replace(base, ai=replace(base.ai, project_id="", api_key=None))
    ai_provider = AIProvider()
    provider = Provider(scope=Scope.APP)
    provider.provide(lambda: settings, provides=Settings)
    provider.provide(lambda: settings.app, provides=AppSettings)
    provider.provide(lambda: settings.ai, provides=AISettings)
    provider.provide(ai_provider.provide_genai_client)
    provider.provide(ai_provider.provide_model_client)
    container = make_async_container(LitestarProvider(), provider)

    app = Litestar(
        route_handlers=[LitestarRouter(path="", route_handlers=[ApexAIController])],
        exception_handlers={AIServiceUnconfigured: ai_service_unconfigured_handler},
        openapi_config=OpenAPIConfig(title="Gateway Unconfigured Test API", version="0.3.1"),
        plugins=[
            ProblemDetailsPlugin(config=ProblemDetailsConfig(enable_for_all_http_exceptions=True)),
            SecurityPlugin(config=replace(build_security_config(settings), exclude=None)),
        ],
    )
    setup_dishka(container, app)
    try:
        async with AsyncTestClient(app=app) as client:
            yield client
    finally:
        await container.close()


def test_openai_wire_schemas_are_frozen_gc_exempt_and_extract_text_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify all OpenAI wire schemas inherit FrozenBaseStruct, skip cyclic GC, and preserve snake_case wire format."""
    schema_types = (
        OpenAITextContentPart,
        OpenAIChatMessage,
        OpenAIChatCompletionRequest,
        OpenAIChatResponseMessage,
        OpenAIChatChoice,
        OpenAIChatStreamDelta,
        OpenAIChatStreamChoice,
        OpenAIChatCompletionChunk,
        OpenAIUsage,
        OpenAIChatCompletionResponse,
        OpenAIModelCard,
        OpenAIModelList,
    )
    for schema_type in schema_types:
        assert issubclass(schema_type, FrozenBaseStruct)

    part = OpenAITextContentPart(text="Recommend a fruity pour-over.")
    msg_from_parts = OpenAIChatMessage(role="user", content=[part, OpenAITextContentPart(text="Keep it light.")])
    msg_from_str = OpenAIChatMessage(role="system", content="You are a Cymbal Coffee barista.")
    msg_empty = OpenAIChatMessage(role="assistant", content=None)
    req = OpenAIChatCompletionRequest(messages=[msg_from_str, msg_from_parts], max_tokens=128)
    resp = OpenAIChatCompletionResponse(
        id="chatcmpl-123",
        created=1767225600,
        model="gemini-3.8-flash",
        choices=[OpenAIChatChoice(index=0, message=OpenAIChatResponseMessage(content="Ethiopian Yirgacheffe"))],
        usage=OpenAIUsage(prompt_tokens=10, completion_tokens=4, total_tokens=14),
    )
    chunk = OpenAIChatCompletionChunk(
        id="chatcmpl-123",
        created=1767225600,
        model="gemini-3.8-flash",
        choices=[OpenAIChatStreamChoice(index=0, delta=OpenAIChatStreamDelta(content="Hi"), finish_reason=None)],
    )
    models = OpenAIModelList(data=[OpenAIModelCard(id="gemini-3.8-flash")])

    for instance in (part, msg_from_parts, msg_from_str, msg_empty, req, resp, chunk, models):
        assert gc.is_tracked(instance) is False

    with pytest.raises(AttributeError):
        setattr(req, "stream", True)

    assert msg_from_str.text_content() == "You are a Cymbal Coffee barista."
    assert msg_from_parts.text_content() == "Recommend a fruity pour-over.\nKeep it light."
    assert not msg_empty.text_content()

    decoded_req = decode_json(
        '{"model":"google/gemini-3.8-flash","messages":[{"role":"user","content":[{"type":"text","text":"Espresso?"}]}]}',
        target_type=OpenAIChatCompletionRequest,
    )
    assert decoded_req.messages[0].text_content() == "Espresso?"

    encoded_resp = decode_json(encode_json(resp))
    assert encoded_resp["object"] == "chat.completion"
    assert encoded_resp["choices"][0]["finish_reason"] == "stop"
    assert encoded_resp["usage"] == {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}

    encoded_delta_role = decode_json(encode_json(OpenAIChatStreamDelta(role="assistant")))
    assert encoded_delta_role == {"role": "assistant"}

    encoded_models = decode_json(encode_json(models))
    assert encoded_models["object"] == "list"
    assert encoded_models["data"][0]["owned_by"] == "google-vertex-ai"

    monkeypatch.delenv("APEX_GATEWAY_API_KEY", raising=False)
    assert AppSettings().APEX_GATEWAY_API_KEY is None
    monkeypatch.setenv("APEX_GATEWAY_API_KEY", "   ")
    assert AppSettings().APEX_GATEWAY_API_KEY is None
    monkeypatch.setenv("APEX_GATEWAY_API_KEY", f"  {TEST_GATEWAY_TOKEN}  ")
    assert AppSettings().APEX_GATEWAY_API_KEY == TEST_GATEWAY_TOKEN


@pytest.mark.parametrize("configured_model", ["gemini-3.8-flash", "google/gemini-3.8-flash"])
async def test_list_models_returns_canonical_and_google_prefixed_cards(configured_model: str) -> None:
    """Verify GET /api/apex/ai/v1/models returns deduplicated bare and google/-prefixed model cards."""
    fake_client = _FakeGeminiModelClient()
    async with _gateway_client(fake_client, chat_model=configured_model) as client:
        response = await client.get("/api/apex/ai/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert [card["id"] for card in payload["data"]] == ["gemini-3.8-flash", "google/gemini-3.8-flash"]
    assert all(card["object"] == "model" and card["owned_by"] == "google-vertex-ai" for card in payload["data"])
    assert fake_client.calls == []


async def test_chat_completions_non_streaming_translates_turns_strips_prefix_and_bypasses_csrf() -> None:
    """Verify non-streaming POST /chat/completions maps OpenAI roles, strips google/, aggregates usage, and skips CSRF."""
    fake_client = _FakeGeminiModelClient(
        events=(
            _event("Try our Ethiopian ", usage=Usage(prompt_tokens=24, output_tokens=4, total_tokens=28)),
            _event("Yirgacheffe pour-over.", usage=Usage(prompt_tokens=24, output_tokens=9, total_tokens=33)),
        )
    )
    async with _gateway_client(fake_client, enable_csrf=True) as client:
        response = await client.post(
            "/api/apex/ai/v1/chat/completions",
            json={
                "model": "google/gemini-3.8-flash",
                "temperature": 0.35,
                "max_tokens": 256,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You are the Cymbal Coffee concierge."},
                    {"role": "developer", "content": "Ground every answer in menu facts."},
                    {"role": "user", "content": [{"type": "text", "text": "What light roasts do you carry?"}]},
                    {"role": "assistant", "content": "We feature bright single-origin coffees."},
                    {"role": "user", "content": "Which one has floral notes?"},
                ],
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["id"].startswith("chatcmpl-")
    assert body["object"] == "chat.completion"
    assert isinstance(body["created"], int)
    assert body["model"] == "google/gemini-3.8-flash"
    assert body["choices"] == [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Try our Ethiopian Yirgacheffe pour-over."},
            "finish_reason": "stop",
        }
    ]
    assert body["usage"] == {"prompt_tokens": 24, "completion_tokens": 9, "total_tokens": 33}

    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["model"] == "gemini-3.8-flash"
    assert call["temperature"] == pytest.approx(0.35)
    assert call["system_instruction"] == "You are the Cymbal Coffee concierge.\n\nGround every answer in menu facts."
    assert call["contents"] == [
        Content(role="user", parts=[Part(text="What light roasts do you carry?")]),
        Content(role="model", parts=[Part(text="We feature bright single-origin coffees.")]),
        Content(role="user", parts=[Part(text="Which one has floral notes?")]),
    ]


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "system", "content": "System instruction without a user turn."}],
        [{"role": "user", "content": "   "}],
        [{"role": "user", "content": [{"type": "text", "text": ""}]}],
    ],
)
async def test_chat_completions_rejects_empty_or_system_only_messages(messages: list[dict[str, Any]]) -> None:
    """Verify POST /chat/completions returns HTTP 400 when no non-empty user or assistant turn is present."""
    fake_client = _FakeGeminiModelClient()
    async with _gateway_client(fake_client) as client:
        response = await client.post(
            "/api/apex/ai/v1/chat/completions", json={"model": "gemini-3.8-flash", "messages": messages}
        )

    assert response.status_code == 400
    assert "At least one user or assistant message is required" in response.text
    assert fake_client.calls == []


async def test_chat_completions_streaming_emits_openai_sse_chunks_and_done_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify stream=True emits OpenAIChatCompletionChunk SSE frames serialized via encode_json and terminates with [DONE]."""
    serialized_objects: list[Any] = []

    def spy_encode_json(value: Any) -> str:
        serialized_objects.append(value)
        return encode_json(value)

    monkeypatch.setattr(apex_ai_controller_module, "encode_json", spy_encode_json)

    fake_client = _FakeGeminiModelClient(events=(_event("Cold Brew "), _event("Nitro")))
    async with (
        _gateway_client(fake_client, enable_csrf=True) as client,
        client.stream(
            "POST",
            "/api/apex/ai/v1/chat/completions",
            json={
                "model": "gemini-3.8-flash",
                "stream": True,
                "messages": [{"role": "user", "content": "Recommend a cold coffee"}],
            },
        ) as response,
    ):
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        data_lines = [line async for line in response.aiter_lines() if line]

    assert data_lines[-1] == "data: [DONE]"
    assert len(data_lines) == 5
    assert all(isinstance(item, OpenAIChatCompletionChunk) for item in serialized_objects)

    parsed_chunks = [decode_json(line.removeprefix("data: ")) for line in data_lines[:-1]]
    assert parsed_chunks[0]["object"] == "chat.completion.chunk"
    assert parsed_chunks[0]["choices"] == [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
    assert parsed_chunks[1]["choices"] == [{"index": 0, "delta": {"content": "Cold Brew "}, "finish_reason": None}]
    assert parsed_chunks[2]["choices"] == [{"index": 0, "delta": {"content": "Nitro"}, "finish_reason": None}]
    assert parsed_chunks[3]["choices"] == [{"index": 0, "delta": {}, "finish_reason": "stop"}]


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        ({}, 401),
        ({"Authorization": "Basic dXNlcjpwYXNz"}, 401),
        ({"Authorization": "Bearer wrong-gateway-secret"}, 401),
        ({"Authorization": f"Bearer {TEST_GATEWAY_TOKEN}"}, 200),
        ({"Authorization": f"bearer {TEST_GATEWAY_TOKEN}"}, 200),
    ],
)
async def test_gateway_bearer_authentication_when_configured(headers: dict[str, str], expected_status: int) -> None:
    """Verify optional APEX_GATEWAY_API_KEY enforces constant-time Bearer auth on /models and /chat/completions."""
    fake_client = _FakeGeminiModelClient(events=(_event("Authenticated response"),))
    async with _gateway_client(fake_client, gateway_api_key=TEST_GATEWAY_TOKEN) as client:
        models_resp = await client.get("/api/apex/ai/v1/models", headers=headers)
        chat_resp = await client.post(
            "/api/apex/ai/v1/chat/completions",
            headers=headers,
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

    assert models_resp.status_code == expected_status
    assert chat_resp.status_code == expected_status


@pytest.mark.parametrize("stream_flag", [False, True])
@pytest.mark.parametrize(
    "error",
    [
        AIServiceUnconfigured("Vertex AI project is not configured."),
        Exception.__new__(DefaultCredentialsError, "Could not automatically determine credentials"),
        RuntimeError("Could not automatically determine credentials"),
    ],
)
async def test_chat_completions_maps_unconfigured_and_credential_errors_to_503(
    stream_flag: bool, error: Exception
) -> None:
    """Verify both non-streaming and streaming completions return HTTP 503 when Vertex AI credentials are missing."""
    fake_client = _FakeGeminiModelClient(error=error)
    async with _gateway_client(fake_client) as client:
        response = await client.post(
            "/api/apex/ai/v1/chat/completions",
            json={
                "model": "gemini-3.8-flash",
                "stream": stream_flag,
                "messages": [{"role": "user", "content": "Recommend an espresso"}],
            },
        )

    assert response.status_code == 503
    payload = response.json()
    assert payload["status_code"] == 503
    assert "not configured" in payload["detail"].lower()


def test_apex_catalog_excludes_ai_gateway_while_main_openapi_tags_gateway() -> None:
    """Verify Litestar's OpenAPI schema tags ApexAIController under 'APEX AI Gateway' while build_apex_catalog excludes it."""
    app = Litestar(
        route_handlers=[LitestarRouter(path="", route_handlers=[ApexController, ApexAIController])],
        openapi_config=OpenAPIConfig(title="Cymbal Coffee API", version="0.3.1"),
    )
    openapi_doc = app.openapi_schema.to_schema()
    assert openapi_doc["paths"]["/api/apex/ai/v1/models"]["get"]["tags"] == ["APEX AI Gateway"]
    assert openapi_doc["paths"]["/api/apex/ai/v1/chat/completions"]["post"]["tags"] == ["APEX AI Gateway"]

    catalog = build_apex_catalog(openapi_doc)
    assert "/api/apex/products" in catalog["paths"]
    assert "/api/apex/ai/v1/models" not in catalog["paths"]
    assert "/api/apex/ai/v1/chat/completions" not in catalog["paths"]


async def test_chat_completions_enforces_401_and_400_before_503_with_real_ai_provider() -> None:
    """Verify Bearer 401 and message 400 checks run before Dishka resolves unconfigured GeminiModelClient (503)."""
    auth_headers = {"Authorization": f"Bearer {TEST_GATEWAY_TOKEN}"}
    async with _unconfigured_ai_provider_client(gateway_api_key=TEST_GATEWAY_TOKEN) as client:
        unauth_resp = await client.post(
            "/api/apex/ai/v1/chat/completions", json={"messages": [{"role": "user", "content": "Hello"}]}
        )
        invalid_resp = await client.post(
            "/api/apex/ai/v1/chat/completions", headers=auth_headers, json={"messages": []}
        )
        valid_resp = await client.post(
            "/api/apex/ai/v1/chat/completions",
            headers=auth_headers,
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

    assert unauth_resp.status_code == 401
    assert invalid_resp.status_code == 400
    assert valid_resp.status_code == 503


async def test_sse_iterator_closes_underlying_model_stream_on_early_disconnect() -> None:
    """Verify _build_sse_iterator closes the pre-fetched model stream iterator when closed mid-stream."""
    fake_client = _FakeGeminiModelClient(events=(_event("First "), _event("Second "), _event("Third")))
    stream_iter = aiter(fake_client.generate_stream([Content(role="user", parts=[Part(text="Hi")])]))
    first_event = await anext(stream_iter)
    sse_iter = aiter(
        ApexAIController._build_sse_iterator(
            first_event=first_event,
            stream_iter=stream_iter,
            completion_id="chatcmpl-close",
            created_ts=1767225600,
            requested_model="gemini-3.8-flash",
        )
    )
    first_frame = await anext(sse_iter)
    assert '"role":"assistant"' in first_frame
    aclose = getattr(sse_iter, "aclose", None)
    assert callable(aclose)
    maybe_coro = aclose()
    assert inspect.isawaitable(maybe_coro)
    await maybe_coro
    assert fake_client.closed_streams == 1

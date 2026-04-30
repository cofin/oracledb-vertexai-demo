# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Phase 4 surface for ADKRunner: 3-arg constructor, closure-bound tools, per-request workflow."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = pytest.mark.anyio


def _allow_vertex_config(monkeypatch: Any, adk_module: Any) -> None:
    settings = MagicMock()
    settings.vertex_ai.PROJECT_ID = "test-project"
    settings.vertex_ai.API_KEY = None
    settings.vertex_ai.CHAT_MODEL = "gemini-2.5-flash-lite"
    monkeypatch.setattr(adk_module, "get_settings", lambda: settings)


def test_runner_constructor_takes_session_service_classifier_persona_manager() -> None:
    from app.domain.chat.services.adk import ADKRunner

    params = inspect.signature(ADKRunner.__init__).parameters
    assert "session_service" in params
    assert "classifier" in params
    assert "persona_manager" in params


def test_runner_stashes_dependencies_on_private_attrs() -> None:
    from app.domain.chat.services.adk import ADKRunner

    session_service = object()
    classifier = object()
    persona_manager = object()
    runner = ADKRunner(
        session_service=session_service,  # type: ignore[arg-type]
        classifier=classifier,  # type: ignore[arg-type]
        persona_manager=persona_manager,  # type: ignore[arg-type]
    )

    assert runner._session_service is session_service
    assert runner._classifier is classifier
    assert runner._persona_manager is persona_manager


def test_make_tool_factories_returns_three_async_callables() -> None:
    from app.domain.chat.services.adk import ADKRunner

    tools_service = MagicMock()
    metric_state: dict[str, Any] = {}
    runner = ADKRunner(
        session_service=MagicMock(),
        classifier=MagicMock(),
        persona_manager=MagicMock(),
    )
    tools = runner._make_tool_factories(tools_service, metric_state)

    assert len(tools) == 3
    names = {fn.__name__ for fn in tools}
    assert names == {"search_products_by_vector", "get_product_details", "get_all_store_locations"}
    for fn in tools:
        assert inspect.iscoroutinefunction(fn)
        assert inspect.getdoc(fn)


async def test_search_products_closure_delegates_to_tools_service() -> None:
    from app.domain.chat.services.adk import ADKRunner

    tools_service = MagicMock()
    tools_service.search_products_by_vector = AsyncMock(
        return_value={"products": [{"id": 1}], "embedding_cache_hit": True, "results_count": 1}
    )
    metric_state: dict[str, Any] = {}
    runner = ADKRunner(session_service=MagicMock(), classifier=MagicMock(), persona_manager=MagicMock())
    tools: list[Callable[..., Any]] = runner._make_tool_factories(tools_service, metric_state)
    search = next(fn for fn in tools if fn.__name__ == "search_products_by_vector")

    result = await search("dark roast", limit=3, similarity_threshold=0.5)

    tools_service.search_products_by_vector.assert_awaited_once_with("dark roast", 3, 0.5)
    assert result["products"] == [{"id": 1}]
    assert metric_state["embedding_cache_hit"] is True


async def test_get_product_details_closure_delegates_to_tools_service() -> None:
    from app.domain.chat.services.adk import ADKRunner

    tools_service = MagicMock()
    tools_service.get_product_details = AsyncMock(return_value={"id": 5, "name": "Espresso"})
    runner = ADKRunner(session_service=MagicMock(), classifier=MagicMock(), persona_manager=MagicMock())
    tools = runner._make_tool_factories(tools_service, {})
    details = next(fn for fn in tools if fn.__name__ == "get_product_details")

    result = await details("5")

    tools_service.get_product_details.assert_awaited_once_with("5")
    assert result == {"id": 5, "name": "Espresso"}


async def test_get_all_store_locations_closure_delegates_to_tools_service() -> None:
    from app.domain.chat.services.adk import ADKRunner

    tools_service = MagicMock()
    tools_service.get_all_store_locations = AsyncMock(return_value=[{"city": "Austin"}])
    runner = ADKRunner(session_service=MagicMock(), classifier=MagicMock(), persona_manager=MagicMock())
    tools = runner._make_tool_factories(tools_service, {})
    locations = next(fn for fn in tools if fn.__name__ == "get_all_store_locations")

    result = await locations()

    tools_service.get_all_store_locations.assert_awaited_once_with()
    assert result == [{"city": "Austin"}]


def test_build_workflow_constructs_llmagent_and_calls_make_workflow(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import ADKRunner

    captured_agent_kwargs: dict[str, Any] = {}
    captured_make_workflow: dict[str, Any] = {}

    class FakeLlmAgent:
        def __init__(self, **kwargs: Any) -> None:
            captured_agent_kwargs.update(kwargs)

    def fake_make_workflow(classifier: Any, agent: Any) -> object:
        captured_make_workflow["classifier"] = classifier
        captured_make_workflow["agent"] = agent
        return "WORKFLOW"

    monkeypatch.setattr(adk_module, "LlmAgent", FakeLlmAgent)
    monkeypatch.setattr(adk_module, "make_workflow", fake_make_workflow)

    classifier = MagicMock()
    runner = ADKRunner(session_service=MagicMock(), classifier=classifier, persona_manager=MagicMock())

    async def fake_tool() -> None: ...

    workflow = runner._build_workflow(instruction="be helpful", temperature=0.5, tools=[fake_tool])

    assert workflow == "WORKFLOW"
    assert captured_agent_kwargs["name"] == "CoffeeAssistant"
    assert captured_agent_kwargs["instruction"] == "be helpful"
    assert captured_agent_kwargs["tools"] == [fake_tool]
    assert captured_agent_kwargs["generate_content_config"].temperature == 0.5
    assert callable(captured_agent_kwargs["before_agent_callback"])
    assert captured_make_workflow["classifier"] is classifier


def test_credential_guard_treats_demo_project_as_unconfigured(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module

    settings = MagicMock()
    settings.vertex_ai.PROJECT_ID = "demo-project"
    settings.vertex_ai.API_KEY = None
    monkeypatch.setattr(adk_module, "get_settings", lambda: settings)

    content = adk_module.credential_guard_callback(MagicMock())

    assert content is not None
    assert content.parts[0].text == "AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file."


async def test_process_request_rejects_placeholder_project_before_adk_run(monkeypatch: Any) -> None:
    from app.domain.chat.exceptions import AIServiceUnconfigured
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import ADKRunner

    settings = MagicMock()
    settings.vertex_ai.PROJECT_ID = "demo-project"
    settings.vertex_ai.API_KEY = None
    monkeypatch.setattr(adk_module, "get_settings", lambda: settings)

    session_service = MagicMock()
    session_service.get_session = AsyncMock()
    runner = ADKRunner(session_service=session_service, classifier=MagicMock(), persona_manager=MagicMock())

    with pytest.raises(AIServiceUnconfigured):
        await runner.process_request(
            query="x",
            user_id="u",
            session_id="s",
            persona="enthusiast",
            tools_service=MagicMock(),
        )

    session_service.get_session.assert_not_called()


async def test_process_request_returns_all_seven_keys(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import ADKRunner

    fake_session = MagicMock()
    fake_session.id = "sess-42"
    fake_session.state = {"intent": "PRODUCT_RAG"}
    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=fake_session)
    session_service.create_session = AsyncMock(return_value=fake_session)

    persona_manager = MagicMock()
    persona_manager.get_system_prompt = MagicMock(return_value="composed instruction")
    persona_manager.get_temperature = MagicMock(return_value=0.7)

    classifier = MagicMock()

    async def fake_events() -> Any:
        event = MagicMock()
        part = MagicMock()
        part.text = "Try our Yirgacheffe."
        event.content.parts = [part]
        event.output = None
        event.partial = False
        yield event

    fake_runner = MagicMock()
    fake_runner.run_async = MagicMock(return_value=fake_events())
    tools_service = MagicMock()
    tools_service.make_response_cache_key = MagicMock(return_value="cache-key")
    tools_service.get_cached_chat_response = AsyncMock(return_value=None)
    tools_service.set_cached_chat_response = AsyncMock()

    monkeypatch.setattr(adk_module, "Runner", lambda **kw: fake_runner)
    monkeypatch.setattr(adk_module, "LlmAgent", lambda **kw: MagicMock())
    monkeypatch.setattr(adk_module, "make_workflow", lambda c, a: MagicMock())
    _allow_vertex_config(monkeypatch, adk_module)

    runner = ADKRunner(session_service=session_service, classifier=classifier, persona_manager=persona_manager)

    result = await runner.process_request(
        query="recommend something",
        user_id="u1",
        session_id="sess-42",
        persona="enthusiast",
        tools_service=tools_service,
    )

    expected_keys = {
        "answer",
        "session_id",
        "response_time_ms",
        "intent_detected",
        "search_metrics",
        "from_cache",
        "embedding_cache_hit",
    }
    assert set(result.keys()) == expected_keys
    assert result["answer"] == "Try our Yirgacheffe."
    assert result["session_id"] == "sess-42"
    assert result["intent_detected"] == "PRODUCT_RAG"
    assert isinstance(result["response_time_ms"], float)
    run_kwargs = fake_runner.run_async.call_args.kwargs
    assert run_kwargs["run_config"].streaming_mode.value == "sse"
    tools_service.set_cached_chat_response.assert_awaited_once()


async def test_process_request_prefers_workflow_output_intent(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import ADKRunner

    fake_session = MagicMock()
    fake_session.id = "sess-output"
    fake_session.state = {}
    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=fake_session)
    session_service.create_session = AsyncMock(return_value=fake_session)

    persona_manager = MagicMock()
    persona_manager.get_system_prompt = MagicMock(return_value="composed instruction")
    persona_manager.get_temperature = MagicMock(return_value=0.7)

    async def fake_events() -> Any:
        event = MagicMock()
        event.output = {"answer": "The boldest option is Dark Roast.", "intent": "PRODUCT_RAG"}
        event.content = None
        event.partial = False
        yield event

    fake_runner = MagicMock()
    fake_runner.run_async = MagicMock(return_value=fake_events())
    tools_service = MagicMock()
    tools_service.make_response_cache_key = MagicMock(return_value="cache-key")
    tools_service.get_cached_chat_response = AsyncMock(return_value=None)
    tools_service.set_cached_chat_response = AsyncMock()

    monkeypatch.setattr(adk_module, "Runner", lambda **kw: fake_runner)
    monkeypatch.setattr(adk_module, "LlmAgent", lambda **kw: MagicMock())
    monkeypatch.setattr(adk_module, "make_workflow", lambda c, a: MagicMock())
    _allow_vertex_config(monkeypatch, adk_module)

    runner = ADKRunner(session_service=session_service, classifier=MagicMock(), persona_manager=persona_manager)

    result = await runner.process_request(
        query="something bold",
        user_id="u1",
        session_id="sess-output",
        persona="enthusiast",
        tools_service=tools_service,
    )

    assert result["answer"] == "The boldest option is Dark Roast."
    assert result["intent_detected"] == "PRODUCT_RAG"


async def test_process_request_returns_cached_response_without_model(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import ADKRunner

    fake_session = MagicMock()
    fake_session.id = "sess-cache"
    fake_session.state = {}
    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=fake_session)
    session_service.create_session = AsyncMock(return_value=fake_session)

    persona_manager = MagicMock()
    tools_service = MagicMock()
    tools_service.make_response_cache_key = MagicMock(return_value="cache-key")
    tools_service.get_cached_chat_response = AsyncMock(
        return_value={
            "answer": "Cached answer",
            "intent_detected": "PRODUCT_RAG",
            "search_metrics": {"results_count": 2},
            "embedding_cache_hit": True,
        }
    )

    def fail_runner(**_kw: Any) -> Any:
        raise AssertionError("Runner should not be constructed on cache hit")

    monkeypatch.setattr(adk_module, "Runner", fail_runner)
    _allow_vertex_config(monkeypatch, adk_module)

    runner = ADKRunner(session_service=session_service, classifier=MagicMock(), persona_manager=persona_manager)

    result = await runner.process_request(
        query="something bold",
        user_id="u1",
        session_id="sess-cache",
        persona="enthusiast",
        tools_service=tools_service,
    )

    assert result["answer"] == "Cached answer"
    assert result["from_cache"] is True
    assert result["embedding_cache_hit"] is True
    assert result["search_metrics"]["results_count"] == 2


async def test_process_request_raises_ai_service_unconfigured_on_credential_error(
    monkeypatch: Any,
) -> None:
    from google.genai import errors as genai_errors

    from app.domain.chat.exceptions import AIServiceUnconfigured
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import ADKRunner

    fake_session = MagicMock()
    fake_session.id = "s"
    fake_session.state = {}
    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=fake_session)
    session_service.create_session = AsyncMock(return_value=fake_session)
    tools_service = MagicMock()
    tools_service.make_response_cache_key = MagicMock(return_value="cache-key")
    tools_service.get_cached_chat_response = AsyncMock(return_value=None)
    tools_service.set_cached_chat_response = AsyncMock()

    persona_manager = MagicMock()
    persona_manager.get_system_prompt = MagicMock(return_value="x")
    persona_manager.get_temperature = MagicMock(return_value=0.7)

    def boom_runner(**_kw: Any) -> Any:
        class _Runner:
            def run_async(self, **__: Any) -> Any:
                async def _gen() -> Any:
                    raise genai_errors.ClientError(
                        code=401,
                        response_json={"error": {"message": "API key not valid"}},
                    )
                    yield  # pragma: no cover

                return _gen()

        return _Runner()

    monkeypatch.setattr(adk_module, "Runner", boom_runner)
    monkeypatch.setattr(adk_module, "LlmAgent", lambda **kw: MagicMock())
    monkeypatch.setattr(adk_module, "make_workflow", lambda c, a: MagicMock())
    _allow_vertex_config(monkeypatch, adk_module)

    runner = ADKRunner(session_service=session_service, classifier=MagicMock(), persona_manager=persona_manager)

    with pytest.raises(AIServiceUnconfigured):
        await runner.process_request(
            query="x",
            user_id="u",
            session_id="s",
            persona="enthusiast",
            tools_service=tools_service,
        )


def test_module_level_tool_functions_are_deleted() -> None:
    from app.domain.chat.services import adk as adk_module

    assert not hasattr(adk_module, "search_products_by_vector"), (
        "module-level search_products_by_vector must be removed"
    )
    assert not hasattr(adk_module, "get_product_details"), "module-level get_product_details must be removed"
    assert not hasattr(adk_module, "ALL_TOOLS"), "ALL_TOOLS constant must be removed"
    assert not hasattr(adk_module, "_resolve_request_container"), "_resolve_request_container helper must be removed"

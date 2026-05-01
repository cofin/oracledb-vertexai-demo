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
        return_value={
            "products": [{"id": 1, "name": "Midnight Brew"}],
            "embedding_cache_hit": True,
            "results_count": 1,
            "vector_query": "dark roast",
            "search_metrics": {"embedding_ms": 12.2, "oracle_ms": 4.4, "tool_ms": 16.6},
        }
    )
    metric_state: dict[str, Any] = {}
    runner = ADKRunner(session_service=MagicMock(), classifier=MagicMock(), persona_manager=MagicMock())
    tools: list[Callable[..., Any]] = runner._make_tool_factories(tools_service, metric_state)
    search = next(fn for fn in tools if fn.__name__ == "search_products_by_vector")

    result = await search("dark roast", limit=3, similarity_threshold=0.5)

    tools_service.search_products_by_vector.assert_awaited_once_with("dark roast", 3, 0.5)
    assert result["products"] == [{"id": 1, "name": "Midnight Brew"}]
    assert metric_state["embedding_cache_hit"] is True
    assert metric_state["search_metrics"]["vector_query"] == "dark roast"
    assert metric_state["search_metrics"]["embedding_ms"] == 12.2
    assert metric_state["search_metrics"]["oracle_ms"] == 4.4
    assert metric_state["search_metrics"]["results_count"] == 1
    assert metric_state["rag_products"] == [{"id": 1, "name": "Midnight Brew"}]


def test_effective_intent_promotes_actual_product_lookup() -> None:
    from app.domain.chat.services import adk as adk_module

    assert (
        adk_module._effective_intent(
            "GENERAL_CONVERSATION",
            {"vector_query": "breakfast", "results_count": 1},
            [],
        )
        == "PRODUCT_RAG"
    )
    assert (
        adk_module._effective_intent(
            "GENERAL_CONVERSATION",
            {},
            [{"sql_key": "vector-search-products"}],
        )
        == "PRODUCT_RAG"
    )


async def test_agent_tools_vector_search_records_query_phase_metrics() -> None:
    from app.domain.chat.services.adk import AgentToolsService

    product_service = MagicMock()
    product_service.search_by_vector = AsyncMock(return_value=[{"id": 1, "name": "Midnight Brew"}])
    vertex_ai_service = MagicMock()
    vertex_ai_service.embedding_model = "gemini-embedding-001"
    vertex_ai_service.get_text_embedding = AsyncMock(return_value=([0.1, 0.2], True))
    metrics_service = MagicMock()
    metrics_service.record_search = AsyncMock()

    tools_service = AgentToolsService(
        driver=MagicMock(),
        product_service=product_service,
        metrics_service=metrics_service,
        vertex_ai_service=vertex_ai_service,
        store_service=MagicMock(),
        cache_service=MagicMock(),
    )

    result = await tools_service.search_products_by_vector("dark roast", limit=2, similarity_threshold=0.4)

    vertex_ai_service.get_text_embedding.assert_awaited_once_with(
        "dark roast",
        task_type="RETRIEVAL_QUERY",
        return_cache_status=True,
    )
    product_service.search_by_vector.assert_awaited_once_with([0.1, 0.2], 0.4, 2)
    metrics_service.record_search.assert_awaited_once()
    metrics = metrics_service.record_search.await_args.args[0]
    assert metrics.user_id == "chat"
    assert metrics.result_count == 1
    assert metrics.embedding_time_ms >= 0
    assert metrics.oracle_time_ms >= 0
    assert result["vector_query"] == "dark roast"
    assert result["embedding_cache_hit"] is True
    assert result["search_metrics"]["vector_query"] == "dark roast"
    assert {"embedding_ms", "oracle_ms", "tool_ms"} <= result["search_metrics"].keys()
    assert result["sql_phases"][0]["sql_key"] == "get-cached-embedding"
    assert result["sql_phases"][0]["binds"]["model"] == vertex_ai_service.embedding_model
    assert result["sql_phases"][0]["cache_status"] == "hit"
    assert result["sql_phases"][1]["sql_key"] == "vector-search-products"
    assert result["sql_phases"][1]["row_count"] == 1
    assert result["sql_phases"][1]["binds"]["query_vector"].startswith("<VECTOR[2 FLOAT32], sha256=")
    assert result["sql_phases"][1]["binds"]["query_vector"].endswith(">")
    assert result["sql_phases"][1]["binds"]["query_vector"] != str([0.1, 0.2])


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

    from app.domain.chat.services.classifier import IntentLabel

    classifier = MagicMock()
    classifier.classify = AsyncMock(return_value=IntentLabel.PRODUCT_RAG)
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

    from app.domain.chat.services.classifier import IntentLabel

    classifier = MagicMock()
    classifier.classify = AsyncMock(return_value=IntentLabel.PRODUCT_RAG)

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
    tools_service.search_products_by_vector = AsyncMock(
        return_value={
            "products": [
                {
                    "id": 8,
                    "name": "Yirgacheffe",
                    "description": "A bright Ethiopian coffee.",
                    "price": 5.25,
                }
            ],
            "embedding_cache_hit": False,
            "results_count": 1,
            "vector_query": "recommend something",
            "search_metrics": {"embedding_ms": 10.0, "oracle_ms": 5.0, "tool_ms": 15.0},
            "sql_phases": [
                {
                    "label": "Oracle vector search",
                    "sql_key": "vector-search-products",
                    "sql": "SELECT * FROM product",
                    "binds": {"query_vector": "<VECTOR[3072 FLOAT32], sha256=abc123, norm=1.0>"},
                    "row_count": 1,
                    "runtime_ms": 5.0,
                    "cache_status": "miss",
                }
            ],
        }
    )

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
        "sql_phases",
    }
    assert set(result.keys()) == expected_keys
    assert "Yirgacheffe" in result["answer"]
    assert result["session_id"] == "sess-42"
    assert result["intent_detected"] == "PRODUCT_RAG"
    sql_keys = {phase["sql_key"] for phase in result["sql_phases"]}
    assert {"get-cached-response", "vector-search-products"} <= sql_keys
    assert isinstance(result["response_time_ms"], float)
    fake_runner.run_async.assert_not_called()
    tools_service.search_products_by_vector.assert_awaited_once_with("recommend something", 3, 0.5)
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
    tools_service.search_products_by_vector = AsyncMock(
        return_value={
            "products": [
                {
                    "id": 9,
                    "name": "Dark Roast",
                    "description": "A bold, smoky menu favorite.",
                    "price": 4.75,
                }
            ],
            "embedding_cache_hit": False,
            "results_count": 1,
            "vector_query": "something bold",
            "search_metrics": {"embedding_ms": 10.0, "oracle_ms": 5.0, "tool_ms": 15.0},
        }
    )

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

    assert "Dark Roast" in result["answer"]
    assert result["intent_detected"] == "PRODUCT_RAG"


async def test_product_rag_response_is_grounded_to_menu_products(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import ADKRunner

    fake_session = MagicMock()
    fake_session.id = "sess-grounded"
    fake_session.state = {}
    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=fake_session)
    session_service.create_session = AsyncMock(return_value=fake_session)

    persona_manager = MagicMock()
    persona_manager.get_system_prompt = MagicMock(return_value="composed instruction")
    persona_manager.get_temperature = MagicMock(return_value=0.7)

    async def fake_events() -> Any:
        event = MagicMock()
        event.output = {
            "answer": "Try the Maple Cloud Latte.",
            "intent": "PRODUCT_RAG",
        }
        event.content = None
        event.partial = False
        yield event

    fake_runner = MagicMock()
    fake_runner.run_async = MagicMock(return_value=fake_events())
    tools_service = MagicMock()
    tools_service.make_response_cache_key = MagicMock(return_value="cache-key")
    tools_service.get_cached_chat_response = AsyncMock(return_value=None)
    tools_service.set_cached_chat_response = AsyncMock()
    tools_service.search_products_by_vector = AsyncMock(
        return_value={
            "products": [
                {
                    "id": 7,
                    "name": "Breakfast Blend",
                    "description": "A smooth, balanced roast for the morning.",
                    "price": 4.5,
                }
            ],
            "embedding_cache_hit": False,
            "results_count": 1,
            "vector_query": "what's good for breakfast?",
            "search_metrics": {"embedding_ms": 10.0, "oracle_ms": 5.0, "tool_ms": 15.0},
        }
    )

    monkeypatch.setattr(adk_module, "Runner", lambda **kw: fake_runner)
    monkeypatch.setattr(adk_module, "LlmAgent", lambda **kw: MagicMock())
    monkeypatch.setattr(adk_module, "make_workflow", lambda c, a: MagicMock())
    _allow_vertex_config(monkeypatch, adk_module)

    runner = ADKRunner(session_service=session_service, classifier=MagicMock(), persona_manager=persona_manager)

    result = await runner.process_request(
        query="what's good for breakfast?",
        user_id="u1",
        session_id="sess-grounded",
        persona="enthusiast",
        tools_service=tools_service,
    )

    assert "Breakfast Blend" in result["answer"]
    assert "Maple Cloud Latte" not in result["answer"]
    assert result["intent_detected"] == "PRODUCT_RAG"
    assert result["search_metrics"]["products_found"] == 1
    assert result["search_metrics"]["vector_query"] == "what's good for breakfast?"
    tools_service.search_products_by_vector.assert_awaited_once_with("what's good for breakfast?", 3, 0.5)


async def test_product_rag_stream_does_not_emit_speculative_model_delta(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import ADKRunner
    from app.domain.chat.services.classifier import IntentLabel

    fake_session = MagicMock()
    fake_session.id = "sess-direct-rag"
    fake_session.state = {}
    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=fake_session)
    session_service.create_session = AsyncMock(return_value=fake_session)

    classifier = MagicMock()
    classifier.classify = AsyncMock(return_value=IntentLabel.PRODUCT_RAG)

    persona_manager = MagicMock()
    persona_manager.get_system_prompt = MagicMock(return_value="composed instruction")
    persona_manager.get_temperature = MagicMock(return_value=0.7)

    def fail_runner(**_kw: Any) -> Any:
        raise AssertionError("Product RAG turns must not stream speculative model text before grounding")

    tools_service = MagicMock()
    tools_service.make_response_cache_key = MagicMock(return_value="cache-key")
    tools_service.get_cached_chat_response = AsyncMock(return_value=None)
    tools_service.set_cached_chat_response = AsyncMock()
    tools_service.search_products_by_vector = AsyncMock(
        return_value={
            "products": [
                {
                    "id": 10,
                    "name": "Wakey Wakey Waffles",
                    "description": "Fluffy, golden waffles.",
                    "price": 7.5,
                }
            ],
            "embedding_cache_hit": False,
            "results_count": 1,
            "vector_query": "hey",
            "search_metrics": {"embedding_ms": 10.0, "oracle_ms": 5.0, "tool_ms": 15.0},
        }
    )

    monkeypatch.setattr(adk_module, "Runner", fail_runner)
    _allow_vertex_config(monkeypatch, adk_module)

    runner = ADKRunner(session_service=session_service, classifier=classifier, persona_manager=persona_manager)

    events = [
        event
        async for event in runner.stream_request(
            query="hey",
            user_id="u1",
            session_id="sess-direct-rag",
            persona="enthusiast",
            tools_service=tools_service,
        )
    ]

    assert [event["type"] for event in events] == ["final"]
    assert "Wakey Wakey Waffles" in events[0]["answer"]
    assert events[0]["intent_detected"] == "PRODUCT_RAG"
    tools_service.search_products_by_vector.assert_awaited_once_with("hey", 3, 0.5)


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


async def test_cached_response_with_product_lookup_metrics_promotes_visible_intent(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import ADKRunner

    fake_session = MagicMock()
    fake_session.id = "sess-cache"
    fake_session.state = {}
    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=fake_session)
    session_service.create_session = AsyncMock(return_value=fake_session)

    tools_service = MagicMock()
    tools_service.make_response_cache_key = MagicMock(return_value="cache-key")
    tools_service.get_cached_chat_response = AsyncMock(
        return_value={
            "answer": "The Wakey Wakey Waffles are a popular choice.",
            "intent_detected": "GENERAL_CONVERSATION",
            "search_metrics": {"vector_query": "breakfast", "results_count": 1},
            "embedding_cache_hit": False,
            "sql_phases": [{"sql_key": "vector-search-products"}],
        }
    )

    def fail_runner(**_kw: Any) -> Any:
        raise AssertionError("Runner should not be constructed on cache hit")

    monkeypatch.setattr(adk_module, "Runner", fail_runner)
    _allow_vertex_config(monkeypatch, adk_module)

    runner = ADKRunner(session_service=session_service, classifier=MagicMock(), persona_manager=MagicMock())

    result = await runner.process_request(
        query="breakfast",
        user_id="u1",
        session_id="sess-cache",
        persona="enthusiast",
        tools_service=tools_service,
    )

    assert result["answer"].startswith("The Wakey Wakey Waffles")
    assert result["intent_detected"] == "PRODUCT_RAG"
    assert result["search_metrics"]["vector_query"] == "breakfast"


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

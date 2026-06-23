# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Cover the ADKRunner streaming-chat surface: closure-bound tools, masked SQL telemetry, and per-request workflow."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.app.domain.chat.services.conftest import (
    allow_vertex_config,
    make_persona_manager,
    make_runner,
    make_session,
    make_session_service,
    make_tools_service,
)

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = pytest.mark.anyio


async def test_search_products_closure_delegates_to_tools_service() -> None:
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
    runner = make_runner()
    tools: list[Callable[..., Any]] = runner._make_tool_factories(tools_service, metric_state)
    search = next(fn for fn in tools if fn.__name__ == "search_products_by_vector")

    result = await search("dark roast", limit=3, similarity_threshold=0.5)

    tools_service.search_products_by_vector.assert_awaited_once_with("dark roast", 3, 0.5, store_id=None)
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


def test_safe_location_context_never_exposes_raw_coordinates() -> None:
    from app.domain.chat.services import adk as adk_module

    safe = adk_module._safe_location_context(
        {
            "city": "Dallas",
            "coordinates": {"latitude": 32.7876, "longitude": -96.7994, "accuracy_meters": 40.0},
        }
    )

    assert safe == {"city": "Dallas", "has_browser_coordinates": True, "accuracy_meters": 40.0}
    assert (
        adk_module._effective_intent(
            "GENERAL_CONVERSATION",
            {},
            [{"sql_key": "vector-search-products"}],
        )
        == "PRODUCT_RAG"
    )


async def test_agent_tools_vector_search_records_query_phase_metrics(mock_driver) -> None:
    from app.domain.chat.services.adk import AgentToolsService

    product_service = MagicMock()
    product_service.search_by_vector = AsyncMock(return_value=[{"id": 1, "name": "Midnight Brew"}])
    vertex_ai_service = MagicMock()
    vertex_ai_service.embedding_model = "gemini-embedding-2"
    vertex_ai_service.get_text_embedding = AsyncMock(return_value=([0.1, 0.2], True))
    metrics_service = MagicMock()
    metrics_service.record_search = AsyncMock()

    tools_service = AgentToolsService(
        driver=mock_driver,
        product_service=product_service,
        metrics_service=metrics_service,
        vertex_ai_service=vertex_ai_service,
        store_service=MagicMock(),
        cache_service=MagicMock(),
    )

    result = await tools_service.search_products_by_vector("dark roast", limit=2, similarity_threshold=0.4)

    vertex_ai_service.get_text_embedding.assert_awaited_once_with(
        "dark roast",
        embedding_purpose="query",
        return_cache_status=True,
    )
    product_service.search_by_vector.assert_awaited_once_with([0.1, 0.2], 0.4, 2, store_id=None)
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


async def test_agent_tools_vector_search_passes_store_id_and_records_store_sql_key(mock_driver) -> None:
    from app.domain.chat.services.adk import AgentToolsService

    product_service = MagicMock()
    product_service.search_by_vector = AsyncMock(
        return_value=[{"id": 1, "name": "Midnight Brew", "store_id": 16}]
    )
    vertex_ai_service = MagicMock()
    vertex_ai_service.embedding_model = "gemini-embedding-2"
    vertex_ai_service.get_text_embedding = AsyncMock(return_value=([0.1, 0.2], False))
    metrics_service = MagicMock()
    metrics_service.record_search = AsyncMock()

    tools_service = AgentToolsService(
        driver=mock_driver,
        product_service=product_service,
        metrics_service=metrics_service,
        vertex_ai_service=vertex_ai_service,
        store_service=MagicMock(),
        cache_service=MagicMock(),
    )

    result = await tools_service.search_products_by_vector(
        "dark roast",
        limit=2,
        similarity_threshold=0.4,
        store_id=16,
    )

    product_service.search_by_vector.assert_awaited_once_with([0.1, 0.2], 0.4, 2, store_id=16)
    assert result["sql_phases"][1]["sql_key"] == "vector-search-products-by-store"
    assert result["sql_phases"][1]["binds"]["store_id"] == 16


async def test_get_product_details_closure_delegates_to_tools_service() -> None:
    tools_service = MagicMock()
    tools_service.get_product_details = AsyncMock(return_value={"id": 5, "name": "Espresso"})
    runner = make_runner()
    tools = runner._make_tool_factories(tools_service, {})
    details = next(fn for fn in tools if fn.__name__ == "get_product_details")

    result = await details("5")

    tools_service.get_product_details.assert_awaited_once_with("5")
    assert result == {"id": 5, "name": "Espresso"}


async def test_get_all_store_locations_closure_delegates_to_tools_service() -> None:
    tools_service = MagicMock()
    tools_service.get_all_store_locations = AsyncMock(return_value=[{"city": "Austin"}])
    runner = make_runner()
    tools = runner._make_tool_factories(tools_service, {})
    locations = next(fn for fn in tools if fn.__name__ == "get_all_store_locations")

    result = await locations()

    tools_service.get_all_store_locations.assert_awaited_once_with()
    assert result == [{"city": "Austin"}]


async def test_store_query_closures_delegate_and_capture_sql_phases() -> None:
    tools_service = MagicMock()
    tools_service.find_stores_by_location = AsyncMock(
        return_value={"stores": [{"city": "Dallas"}], "sql_phases": [{"sql_key": "find-stores-by-location"}]}
    )
    tools_service.get_store_hours = AsyncMock(
        return_value={"hours": {"monday": "6am-8pm"}, "sql_phases": [{"sql_key": "get-store-by-id"}]}
    )
    tools_service.find_nearest_stores = AsyncMock(
        return_value={"stores": [{"city": "Dallas"}], "sql_phases": [{"sql_key": "list-stores"}]}
    )
    tools_service.find_stores_with_product = AsyncMock(
        return_value={
            "availability": [{"store_city": "Dallas"}],
            "sql_phases": [{"sql_key": "find-product-availability-by-query"}],
        }
    )
    metric_state: dict[str, Any] = {"sql_phases": []}
    runner = make_runner()
    tools = runner._make_tool_factories(tools_service, metric_state)
    by_name = {fn.__name__: fn for fn in tools}

    await by_name["find_stores_by_location"](city="Dallas", state="TX", zip_code="75201")
    await by_name["get_store_hours"](16)
    await by_name["find_nearest_stores"](32.78, -96.8)
    await by_name["find_stores_with_product"]("Espresso Romano", latitude=32.78, longitude=-96.8)

    tools_service.find_stores_by_location.assert_awaited_once_with(city="Dallas", state="TX", zip_code="75201")
    tools_service.get_store_hours.assert_awaited_once_with(16)
    tools_service.find_nearest_stores.assert_awaited_once_with(32.78, -96.8, 5)
    tools_service.find_stores_with_product.assert_awaited_once_with("Espresso Romano", 32.78, -96.8)
    assert [phase["sql_key"] for phase in metric_state["sql_phases"]] == [
        "find-stores-by-location",
        "get-store-by-id",
        "list-stores",
        "find-product-availability-by-query",
    ]


async def test_agent_tools_store_query_results_include_masked_sql_phases(mock_driver) -> None:
    from app.domain.chat.services.adk import AgentToolsService

    store_service = MagicMock()
    store_service.find_nearest_stores = AsyncMock(return_value=[{"id": 16, "name": "Cymbal Coffee Dallas"}])
    tools_service = AgentToolsService(
        driver=mock_driver,
        product_service=MagicMock(),
        metrics_service=MagicMock(),
        vertex_ai_service=MagicMock(),
        store_service=store_service,
        cache_service=MagicMock(),
    )

    result = await tools_service.find_nearest_stores(32.78, -96.8)

    store_service.find_nearest_stores.assert_awaited_once_with(32.78, -96.8, 5)
    assert result["stores"] == [{"id": 16, "name": "Cymbal Coffee Dallas"}]
    assert result["sql_phases"][0]["sql_key"] == "list-stores"
    assert result["sql_phases"][0]["binds"] == {"origin": "<REQUEST_COORDINATES>", "limit": 5}


async def test_stream_request_skips_response_cache_for_safe_location_context(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.domain.chat.services import adk as adk_module

    allow_vertex_config(monkeypatch, adk_module)
    session_service = make_session_service(session=make_session())
    tools_service = make_tools_service()
    tools_service.get_cached_chat_response = AsyncMock()
    tools_service.make_response_cache_key = MagicMock(return_value="chat:key")
    classifier = MagicMock()
    classifier.classify.return_value = "ORDER_STATUS"
    runner = make_runner(session_service=session_service, classifier=classifier)

    events = [
        event
        async for event in runner.stream_request(
            "where can I get an order in Dallas?",
            user_id="u1",
            session_id="s1",
            persona="friendly",
            tools_service=tools_service,
            location_context={"city": "Dallas"},
        )
    ]

    assert events[-1]["intent_detected"] == "ORDER_STATUS"
    tools_service.make_response_cache_key.assert_not_called()
    tools_service.get_cached_chat_response.assert_not_awaited()


def test_build_workflow_wires_agent_instruction_temperature_and_credential_guard() -> None:
    from google.adk import Workflow

    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.classifier import IntentLabel

    classifier = MagicMock()
    classifier.classify = AsyncMock(return_value=IntentLabel.PRODUCT_RAG)
    runner = make_runner(classifier=classifier)

    async def fake_tool() -> None: ...

    workflow = runner._build_workflow(instruction="be helpful", temperature=0.5, tools=[fake_tool])

    assert isinstance(workflow, Workflow)
    agent = next(
        edge[1]
        for edge in workflow.edges
        if getattr(edge[1], "instruction", None) == "be helpful"
    )
    assert agent.tools == [fake_tool]
    assert agent.generate_content_config.temperature == 0.5
    assert agent.before_agent_callback is adk_module.credential_guard_callback


def test_credential_guard_treats_demo_project_as_unconfigured(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module

    settings = MagicMock()
    settings.ai.project_id = "demo-project"
    settings.ai.api_key = None
    monkeypatch.setattr(adk_module, "get_settings", lambda: settings)

    content = adk_module.credential_guard_callback(MagicMock())

    assert content is not None
    assert content.parts[0].text == "AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file."


async def test_product_rag_stream_does_not_emit_speculative_model_delta(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module

    def fail_runner(**_kw: Any) -> Any:
        raise AssertionError("Product RAG turns must not stream speculative model text before grounding")

    tools_service = make_tools_service(
        products=[
            {
                "id": 10,
                "name": "Wakey Wakey Waffles",
                "description": "Fluffy, golden waffles.",
                "price": 7.5,
            }
        ],
        vector_query="hey",
    )

    monkeypatch.setattr(adk_module, "Runner", fail_runner)
    allow_vertex_config(monkeypatch, adk_module)

    runner = make_runner(
        session_service=make_session_service(make_session("sess-direct-rag")),
    )

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
    tools_service.search_products_by_vector.assert_awaited_once_with("hey", 3, 0.5, store_id=None)


async def test_general_conversation_relabels_to_product_rag_after_tool_lookup(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.classifier import IntentLabel

    classifier = MagicMock()
    classifier.classify = AsyncMock(return_value=IntentLabel.GENERAL_CONVERSATION)

    tools_service = make_tools_service(
        products=[
            {
                "id": 11,
                "name": "Caramel Cloud Latte",
                "description": "Silky caramel latte.",
                "price": 6.25,
            }
        ],
        vector_query="something sweet",
    )

    captured_tools: dict[str, Any] = {}

    class FakeRunner:
        def __init__(self, *, node: Any, app_name: str, session_service: Any) -> None:
            del node, app_name, session_service

        def run_async(self, **_kw: Any) -> Any:
            async def _events() -> Any:
                # The model calls the vector tool, populating metric_state via the closure.
                search = next(fn for fn in captured_tools["tools"] if fn.__name__ == "search_products_by_vector")
                await search("something sweet")
                yield SimpleNamespace(output={"intent": "GENERAL_CONVERSATION", "answer": ""}, content=None, partial=False)

            return _events()

    runner = make_runner(
        session_service=make_session_service(make_session("sess-relabel")),
        classifier=classifier,
    )
    original_make_tool_factories = runner._make_tool_factories

    def capture_tools(
        tools_service: Any,
        metric_state: dict[str, Any],
        location_context: dict[str, Any] | None = None,
    ) -> Any:
        tools = original_make_tool_factories(tools_service, metric_state, location_context)
        captured_tools["tools"] = tools
        return tools

    monkeypatch.setattr(runner, "_make_tool_factories", capture_tools)
    monkeypatch.setattr(adk_module, "Runner", FakeRunner)
    allow_vertex_config(monkeypatch, adk_module)

    events = [
        event
        async for event in runner.stream_request(
            query="something sweet",
            user_id="u1",
            session_id="sess-relabel",
            persona="enthusiast",
            tools_service=tools_service,
        )
    ]

    final = events[-1]
    assert final["type"] == "final"
    assert final["intent_detected"] == "PRODUCT_RAG"
    assert "Caramel Cloud Latte" in final["answer"]
    assert final["search_metrics"]["vector_query"] == "something sweet"
    assert any(phase["sql_key"] == "vector-search-products" for phase in final["sql_phases"])
    assert final["from_cache"] is False


async def test_set_cached_chat_response_uses_chat_settings_ttl(mock_driver, monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import AgentToolsService

    settings = MagicMock()
    settings.chat.response_cache_ttl_minutes = 17
    monkeypatch.setattr(adk_module, "get_settings", lambda: settings)

    cache_service = MagicMock()
    cache_service.set_cached_response = AsyncMock()
    tools_service = AgentToolsService(
        driver=mock_driver,
        product_service=MagicMock(),
        metrics_service=MagicMock(),
        vertex_ai_service=MagicMock(),
        store_service=MagicMock(),
        cache_service=cache_service,
    )

    await tools_service.set_cached_chat_response("cache-key", {"answer": "hi"})

    cache_service.set_cached_response.assert_awaited_once_with("cache-key", {"answer": "hi"}, ttl_minutes=17)


async def test_make_response_cache_key_uses_chat_settings_version(mock_driver, monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module
    from app.domain.chat.services.adk import AgentToolsService

    settings = MagicMock()
    settings.chat.response_cache_version = "custom-vN"
    monkeypatch.setattr(adk_module, "get_settings", lambda: settings)

    vertex_ai_service = MagicMock()
    vertex_ai_service.model = "gemini-3.1-flash-lite"
    tools_service = AgentToolsService(
        driver=mock_driver,
        product_service=MagicMock(),
        metrics_service=MagicMock(),
        vertex_ai_service=vertex_ai_service,
        store_service=MagicMock(),
        cache_service=MagicMock(),
    )

    from hashlib import sha256

    expected_digest = sha256(b"custom-vN:gemini-3.1-flash-lite:enthusiast:latte").hexdigest()
    assert tools_service.make_response_cache_key("latte", "enthusiast") == f"chat:{expected_digest}"


async def test_append_display_history_truncates_to_chat_settings_limit(monkeypatch: Any) -> None:
    from app.domain.chat.services import adk as adk_module

    settings = MagicMock()
    settings.chat.display_history_limit = 3
    monkeypatch.setattr(adk_module, "get_settings", lambda: settings)

    prior = [{"source": "human" if i % 2 == 0 else "ai", "message": f"m{i}"} for i in range(10)]
    captured: dict[str, Any] = {}

    def update_session_state(session_id: str, state: dict[str, Any]) -> None:
        captured["state"] = state

    session_service = SimpleNamespace(
        get_session=AsyncMock(return_value=make_session("sess-trunc", {"display_history": prior})),
        store=SimpleNamespace(update_session_state=update_session_state),
    )
    runner = make_runner(session_service=session_service, persona_manager=make_persona_manager())

    await runner._append_display_history(
        user_id="u1",
        session_id="sess-trunc",
        query="latest question",
        answer="latest answer",
        intent_detected="PRODUCT_RAG",
    )

    history = captured["state"]["display_history"]
    assert len(history) == 3
    assert history[-1] == {"source": "ai", "message": "latest answer"}
    assert history[-2] == {"source": "human", "message": "latest question"}

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for grounded AI tools and AgentOrchestrationService hybrid routing."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.domain.ai.runtime import (
    AgentEvent,
    AgentRuntime,
    AgentStreamService,
    CallContext,
    CoffeeToolContext,
    Content,
    Part,
    Usage,
)
from app.domain.ai.services import AgentOrchestrationService, build_coffee_tools, get_coffee_spec_tree
from app.domain.ai.services._history import extract_last_products, extract_session_state, has_session_context
from app.domain.chat.schemas import HybridProductCandidate, HybridTurnContext
from app.domain.chat.services import GroundedRouteService
from app.domain.products.schemas import Product

pytestmark = pytest.mark.anyio


class _FakeModelClient:
    async def generate_stream(self, *args: Any, **kwargs: Any) -> AsyncGenerator[AgentEvent, None]:
        del args, kwargs
        yield AgentEvent(
            session_id="s1",
            invocation_id="inv1",
            agent="coffee_barista",
            turn=1,
            partial=True,
            content=Content(role="model", parts=[Part(text="Here is a coffee joke!")]),
            usage=Usage(prompt_tokens=10, output_tokens=6, total_tokens=16),
        )


def test_get_coffee_spec_tree_registers_five_grounded_tools() -> None:
    """Verify get_coffee_spec_tree registers all 5 grounded coffee tools and private _agent/_history boundaries."""
    assert AgentOrchestrationService.__module__ == "app.domain.ai.services._agent"
    assert extract_session_state({"state": '{"last_products":["Espresso"]}'}) == {"last_products": ["Espresso"]}
    assert extract_last_products({"last_products": ["Espresso", " "]}) == ["Espresso"]
    assert has_session_context([], {"last_products": ["Espresso"]}) is True

    tree = get_coffee_spec_tree()
    tool_names = [tool.name for tool in tree.root.tools]
    assert tool_names == [
        "search_products",
        "get_product_details",
        "find_nearby_stores",
        "check_product_availability",
        "check_order_status",
    ]
    for tool in tree.root.tools:
        decl = tool.declaration()
        assert decl.parameters_json_schema["type"] == "object"
        assert "properties" in decl.parameters_json_schema


async def test_grounded_tools_execute_against_services_without_leaking_coordinates() -> None:
    """Verify each of the 5 grounded tools executes against CoffeeToolContext and masks coordinates."""
    product_service = AsyncMock()
    store_service = AsyncMock()
    vertex_ai_service = AsyncMock()
    metrics_service = AsyncMock()

    vertex_ai_service.get_text_embedding.return_value = ([0.1] * 3072, True)
    product_service.search_hybrid.return_value = []
    product_service.get_by_id.return_value = Product(
        id=1, name="Velvet Espresso", price=16.50, description="Bold dark roast.", category="Whole Bean"
    )
    store_service.find_nearest_stores.return_value = []
    store_service.find_product_availability.return_value = []

    tools = {tool.name: tool for tool in build_coffee_tools()}
    ctx = CallContext(
        session_id="s1",
        invocation_id="inv1",
        turn=1,
        state={"location_context": {"city": "Dallas", "coordinates": {"latitude": 32.75, "longitude": -96.83}}},
        services=CoffeeToolContext(
            product_service=product_service,
            store_service=store_service,
            vertex_ai_service=vertex_ai_service,
            metrics_service=metrics_service,
        ),
    )

    search_res = await tools["search_products"].invoke({"query": "dark roast", "limit": 3}, ctx)
    assert search_res["results_count"] == 0

    details_res = await tools["get_product_details"].invoke({"product_id_or_name": "1"}, ctx)
    assert details_res["name"] == "Velvet Espresso"

    stores_res = await tools["find_nearby_stores"].invoke({"city": "Dallas"}, ctx)
    assert stores_res["results_count"] == 0
    store_service.find_nearest_stores.assert_awaited_once_with(32.75, -96.83, 5)

    avail_res = await tools["check_product_availability"].invoke({"product_query": "Velvet Espresso"}, ctx)
    assert avail_res["results_count"] == 0

    order_res = await tools["check_order_status"].invoke({"order_id": "1042"}, ctx)
    assert order_res["supported"] is False
    assert "does not include order tracking" in order_res["message"]


async def test_orchestrator_deterministic_hybrid_route_short_circuits_agent_loop() -> None:
    """Deterministic PRODUCT_RAG turn uses HybridRouteResolver + GroundedRouteService, caches, and records metrics."""
    session_store = AsyncMock()
    session_store.get_session.return_value = None
    event_store = AsyncMock()
    event_store.list_events.return_value = []
    event_store.get_next_seq.return_value = 1

    route_resolver = AsyncMock()
    route_resolver.resolve_turn.return_value = HybridTurnContext(
        user_message="Do you have Folgers?",
        oracle_text_query="{folgers}",
        intent_detected="PRODUCT_RAG",
        is_deterministic=True,
        route_confidence=0.0328,
        products=[
            HybridProductCandidate(
                id=1,
                name="Velvet Espresso",
                description="Bold dark roast.",
                category="Whole Bean",
                price=16.50,
                rrf_score=0.01639,
                vector_similarity=0.82,
                vector_rank=1,
            )
        ],
        term_hits={"folgers": 0},
        off_menu_terms=["folgers"],
        oracle_time_ms=7.5,
    )

    product_service = AsyncMock()
    store_service = AsyncMock()
    vertex_ai_service = AsyncMock()
    vertex_ai_service.model = "gemini-3.8-flash"
    vertex_ai_service.embedding_model = "gemini-embedding-2"
    vertex_ai_service.get_text_embedding.return_value = ([0.05] * 3072, True)

    cache_service = AsyncMock()
    cache_service.get_cached_response.return_value = None
    metrics_service = AsyncMock()

    grounded_service = GroundedRouteService(
        product_service=product_service, store_service=store_service, vertex_ai_service=vertex_ai_service
    )

    orchestrator = AgentOrchestrationService(
        runtime=AgentRuntime(model_client=_FakeModelClient()),
        stream_service=AgentStreamService(),
        spec_tree=get_coffee_spec_tree(),
        session_store=session_store,
        event_store=event_store,
        route_resolver=route_resolver,
        grounded_service=grounded_service,
        product_service=product_service,
        store_service=store_service,
        vertex_ai_service=vertex_ai_service,
        cache_service=cache_service,
        metrics_service=metrics_service,
    )

    final_frame = await orchestrator.run_conversation_turn(
        session_id="sess-1", user_id="user-1", message="Do you have Folgers?", persona="barista"
    )

    assert final_frame["type"] == "final"
    assert final_frame["intent_detected"] == "PRODUCT_RAG"
    assert "does not carry Folgers" in final_frame["answer"]
    assert final_frame["embedding_cache_hit"] is True
    assert final_frame["from_cache"] is False
    metrics_service.record_search.assert_awaited_once()
    cache_service.set_cached_response.assert_awaited_once()
    assert event_store.append_event.await_count == 2


async def test_orchestrator_skips_response_cache_when_location_present_and_never_persists_coordinates() -> None:
    """Location-scoped turns bypass CacheService and strip raw coordinates from persisted state."""
    session_store = AsyncMock()
    session_store.get_session.return_value = None
    event_store = AsyncMock()
    event_store.list_events.return_value = []
    event_store.get_next_seq.return_value = 1

    route_resolver = AsyncMock()
    route_resolver.resolve_turn.return_value = HybridTurnContext(
        user_message="Tell me a coffee joke",
        oracle_text_query="{tell} ACCUM {coffee} ACCUM {joke}",
        intent_detected="GENERAL_CONVERSATION",
        is_deterministic=False,
        route_confidence=0.0328,
        oracle_time_ms=4.0,
    )

    vertex_ai_service = AsyncMock()
    vertex_ai_service.model = "gemini-3.8-flash"
    vertex_ai_service.embedding_model = "gemini-embedding-2"
    vertex_ai_service.get_text_embedding.return_value = ([0.05] * 3072, False)

    cache_service = AsyncMock()
    metrics_service = AsyncMock()

    orchestrator = AgentOrchestrationService(
        runtime=AgentRuntime(model_client=_FakeModelClient()),
        stream_service=AgentStreamService(),
        spec_tree=get_coffee_spec_tree(),
        session_store=session_store,
        event_store=event_store,
        route_resolver=route_resolver,
        vertex_ai_service=vertex_ai_service,
        cache_service=cache_service,
        metrics_service=metrics_service,
    )

    raw_loc = {"city": "Dallas", "coordinates": {"latitude": 32.7767, "longitude": -96.7970, "accuracy_meters": 12.0}}
    final_frame = await orchestrator.run_conversation_turn(
        session_id="sess-loc", user_id="user-1", message="Tell me a coffee joke", location_context=raw_loc
    )

    assert final_frame["type"] == "final"
    assert final_frame["answer"] == "Here is a coffee joke!"
    assert "ai_ms" in final_frame["search_metrics"]
    assert "coordinates" not in final_frame["location_context"]
    assert "32.7767" not in str(final_frame)
    cache_service.get_cached_response.assert_not_awaited()
    cache_service.set_cached_response.assert_not_awaited()
    for call in event_store.append_event.await_args_list:
        assert "32.7767" not in str(call)


async def test_orchestrator_skips_response_cache_for_multi_turn_session_with_history() -> None:
    """Multi-turn follow-ups with conversation history bypass global response cache read and write."""
    session_store = AsyncMock()
    session_store.get_session.return_value = {"id": "sess-multi", "state": {"last_products": ["Velvet Espresso"]}}
    event_store = AsyncMock()
    event_store.list_events.return_value = [
        AgentEvent(
            session_id="sess-multi",
            invocation_id="inv-prev",
            agent="user",
            seq=1,
            turn=1,
            content=Content(role="user", parts=[Part(text="Recommend a dark roast")]),
        ),
        AgentEvent(
            session_id="sess-multi",
            invocation_id="inv-prev",
            agent="coffee_barista",
            seq=2,
            turn=1,
            content=Content(role="model", parts=[Part(text="Try Velvet Espresso.")]),
        ),
    ]
    event_store.get_next_seq.return_value = 3

    route_resolver = AsyncMock()
    route_resolver.resolve_turn.return_value = HybridTurnContext(
        user_message="Where is it in stock?",
        oracle_text_query="{stock}",
        intent_detected="GENERAL_CONVERSATION",
        is_deterministic=False,
        route_confidence=0.45,
        oracle_time_ms=3.5,
    )

    vertex_ai_service = AsyncMock()
    vertex_ai_service.get_text_embedding.return_value = ([0.05] * 3072, True)
    store_service = AsyncMock()
    cache_service = AsyncMock()

    orchestrator = AgentOrchestrationService(
        runtime=AgentRuntime(model_client=_FakeModelClient()),
        stream_service=AgentStreamService(),
        spec_tree=get_coffee_spec_tree(),
        session_store=session_store,
        event_store=event_store,
        route_resolver=route_resolver,
        store_service=store_service,
        vertex_ai_service=vertex_ai_service,
        cache_service=cache_service,
    )

    tool_ctx = orchestrator._build_tool_services(None)
    assert tool_ctx.store_service is store_service
    assert not hasattr(tool_ctx, "inventory_service")

    final_frame = await orchestrator.run_conversation_turn(
        session_id="sess-multi", user_id="user-1", message="Where is it in stock?", persona="barista"
    )
    assert final_frame["type"] == "final"
    assert final_frame["from_cache"] is False
    cache_service.get_cached_response.assert_not_awaited()
    cache_service.set_cached_response.assert_not_awaited()


async def test_get_display_history_verifies_session_ownership_and_applies_limit() -> None:
    """get_display_history checks user ownership on session_store and passes display_history_limit."""
    session_store = AsyncMock()
    session_store.get_session.side_effect = [None, {"id": "sess-owned", "user_id": "user-1"}]
    event_store = AsyncMock()
    event_store.list_events.return_value = [
        AgentEvent(
            session_id="sess-owned",
            invocation_id="inv-1",
            agent="user",
            seq=1,
            turn=1,
            content=Content(role="user", parts=[Part(text="Hello barista")]),
        ),
        AgentEvent(
            session_id="sess-owned",
            invocation_id="inv-1",
            agent="coffee_barista",
            seq=2,
            turn=1,
            content=Content(role="model", parts=[Part(text="Welcome to Cymbal Coffee!")]),
        ),
    ]

    orchestrator = AgentOrchestrationService(
        runtime=AgentRuntime(model_client=_FakeModelClient()),
        stream_service=AgentStreamService(),
        spec_tree=get_coffee_spec_tree(),
        session_store=session_store,
        event_store=event_store,
    )

    unowned = await orchestrator.get_display_history("sess-other", user_id="user-1")
    assert unowned == []
    event_store.list_events.assert_not_awaited()

    owned = await orchestrator.get_display_history("sess-owned", user_id="user-1")
    assert len(owned) == 2
    assert owned[0].source == "human"
    assert owned[1].source == "ai"
    event_store.list_events.assert_awaited_once()
    assert "limit" in event_store.list_events.await_args.kwargs

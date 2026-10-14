# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Behavioral unit tests for grounded route composers and hybrid telemetry builders."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.domain.chat.schemas import HybridProductCandidate, HybridStoreCandidate, HybridTurnContext
from app.domain.chat.services._grounded import GroundedRouteService
from app.domain.chat.services._telemetry import (
    SearchMetrics,
    SQLPhase,
    build_hybrid_sql_phases,
    build_response_cache_phase,
    build_search_metrics,
    safe_location_context,
)
from app.domain.products.schemas import ProductAvailability, Store, StoreDistance

pytestmark = pytest.mark.anyio

_NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)


def _make_turn_context(
    *,
    user_message: str = "Recommend a coffee",
    intent_detected: str = "PRODUCT_RAG",
    is_deterministic: bool = True,
    products: list[HybridProductCandidate] | None = None,
    stores: list[HybridStoreCandidate] | None = None,
    term_hits: dict[str, int] | None = None,
    off_menu_terms: list[str] | None = None,
    oracle_text_query: str | None = "{velvet} ACCUM {espresso}",
) -> HybridTurnContext:
    return HybridTurnContext(
        user_message=user_message,
        oracle_text_query=oracle_text_query,
        intent_detected=intent_detected,  # type: ignore[arg-type]
        is_deterministic=is_deterministic,
        route_confidence=0.0328,
        products=products or [],
        stores=stores or [],
        term_hits=term_hits or {},
        off_menu_terms=off_menu_terms or [],
    )


async def test_handle_product_rag_off_menu_folgers_guard() -> None:
    """Zero-hit brand terms like Folgers trigger deterministic off-menu response without LLM call."""
    store_service = AsyncMock()
    product_service = AsyncMock()
    vertex_ai_service = AsyncMock()

    service = GroundedRouteService(
        product_service=product_service, store_service=store_service, vertex_ai_service=vertex_ai_service
    )
    candidates = [
        HybridProductCandidate(
            id=1,
            name="Velvet Espresso",
            category="Whole Bean",
            price=16.50,
            description="Bold dark roast with bittersweet cocoa and caramelized sugar notes.",
            rrf_score=0.01639,
            lexical_score=0.0,
            vector_similarity=0.81,
            lexical_rank=None,
            vector_rank=1,
        ),
        HybridProductCandidate(
            id=2,
            name="Midnight Oil Dark",
            category="Whole Bean",
            price=15.75,
            description="Smoky dark roast with molasses depth.",
            rrf_score=0.01612,
            lexical_score=0.0,
            vector_similarity=0.78,
            lexical_rank=None,
            vector_rank=2,
        ),
    ]
    turn_ctx = _make_turn_context(
        user_message="Do you have Folgers?",
        intent_detected="PRODUCT_RAG",
        products=candidates,
        term_hits={"folgers": 0},
        off_menu_terms=["folgers"],
        oracle_text_query="{folgers}",
    )

    result = await service.handle_product_rag("Do you have Folgers?", turn_ctx, embedding_ms=12.4, oracle_ms=8.2)

    assert result.intent_detected == "PRODUCT_RAG"
    assert "does not carry Folgers" in result.answer
    assert "Velvet Espresso ($16.50)" in result.answer
    assert "Midnight Oil Dark ($15.75)" in result.answer
    vertex_ai_service.generate_structured_content.assert_not_called()
    assert result.search_metrics.grounded_answer_mode == "off_menu_guard"


async def test_handle_product_rag_in_catalog_recommendation() -> None:
    """In-catalog RRF matches synthesize a grounded recommendation referencing matched items and prices."""
    store_service = AsyncMock()
    product_service = AsyncMock()
    vertex_ai_service = AsyncMock()
    vertex_ai_service.generate_structured_content.return_value = type(
        "FakeResp",
        (),
        {
            "parsed": {
                "mode": "recommend",
                "selected_product_ids": ["1", "2"],
                "off_menu_term": "",
                "explanation": "These bright Ethiopian beans are ideal for pour-over brewing.",
            }
        },
    )()

    service = GroundedRouteService(
        product_service=product_service, store_service=store_service, vertex_ai_service=vertex_ai_service
    )
    candidates = [
        HybridProductCandidate(
            id=1,
            name="Addis Ababa Sunrise",
            category="Single Origin",
            price=18.00,
            description="Bright bergamot and jasmine notes.",
            rrf_score=0.03278,
            lexical_score=88.0,
            vector_similarity=0.89,
            lexical_rank=1,
            vector_rank=1,
        ),
        HybridProductCandidate(
            id=2,
            name="Yirgacheffe Bloom",
            category="Single Origin",
            price=19.50,
            description="Delicate peach and floral tea finish.",
            rrf_score=0.03225,
            lexical_score=76.0,
            vector_similarity=0.85,
            lexical_rank=2,
            vector_rank=2,
        ),
    ]
    turn_ctx = _make_turn_context(
        user_message="Recommend a bright Ethiopian pour-over",
        intent_detected="PRODUCT_RAG",
        products=candidates,
        term_hits={"ethiopian": 2},
    )

    result = await service.handle_product_rag(
        "Recommend a bright Ethiopian pour-over", turn_ctx, persona="snob", embedding_ms=10.0, oracle_ms=6.5
    )

    assert result.intent_detected == "PRODUCT_RAG"
    assert "Addis Ababa Sunrise ($18.00)" in result.answer
    assert "Yirgacheffe Bloom ($19.50)" in result.answer
    assert "These bright Ethiopian beans" in result.answer
    assert result.search_metrics.products_found == 2
    assert result.search_metrics.grounded_answer_mode == "structured"


async def test_handle_store_location_masks_browser_coordinates() -> None:
    """STORE_LOCATION populates store_results and map_actions while keeping coordinates out of location_context."""
    store_service = AsyncMock()
    product_service = AsyncMock()
    store_service.find_nearest_stores.return_value = [
        StoreDistance(
            id=10,
            name="Cymbal Coffee Bishop Arts",
            address="408 N Bishop Ave",
            created_at=_NOW,
            updated_at=_NOW,
            city="Dallas",
            state="TX",
            zip="75208",
            phone="214-555-0142",
            latitude=32.7478,
            longitude=-96.8289,
            timezone="America/Chicago",
            google_place_id="place_bishop_arts",
            hours={"monday": "6:30 AM - 7:00 PM"},
            distance_miles=1.4,
        )
    ]

    service = GroundedRouteService(product_service=product_service, store_service=store_service)
    turn_ctx = _make_turn_context(
        user_message="Where is the closest Dallas coffee shop?",
        intent_detected="STORE_LOCATION",
        stores=[
            HybridStoreCandidate(
                id=10,
                name="Cymbal Coffee Bishop Arts",
                city="Dallas",
                state="TX",
                address="408 N Bishop Ave, Dallas, TX 75208",
                rrf_score=0.01639,
                lexical_score=85.0,
                lexical_rank=1,
            )
        ],
    )
    raw_location_context = {
        "city": "Dallas",
        "state": "TX",
        "coordinates": {"latitude": 32.7512, "longitude": -96.8311, "accuracy_meters": 15.0},
    }

    result = await service.handle_store_location(
        "Where is the closest Dallas coffee shop?", turn_ctx, location_context=raw_location_context
    )

    assert result.intent_detected == "STORE_LOCATION"
    assert "Cymbal Coffee Bishop Arts" in result.answer
    assert "408 N Bishop Ave" in result.answer
    assert len(result.store_results) == 1
    assert len(result.map_actions) == 2
    assert result.map_actions[0]["type"] == "search"
    assert result.map_actions[1]["type"] == "directions"
    assert "coordinates" not in result.location_context
    assert "latitude" not in str(result.location_context)
    assert "longitude" not in str(result.location_context)
    assert result.location_context["has_browser_coordinates"] is True


async def test_handle_product_availability_populates_inventory_and_maps() -> None:
    """PRODUCT_AVAILABILITY returns store inventory rows, map actions, and masked location context."""
    store_service = AsyncMock()
    product_service = AsyncMock()
    store_service.resolve_store.return_value = Store(
        id=10,
        name="Cymbal Coffee Bishop Arts",
        address="408 N Bishop Ave",
        created_at=_NOW,
        updated_at=_NOW,
        city="Dallas",
        state="TX",
        zip="75208",
        phone="214-555-0142",
        latitude=32.7478,
        longitude=-96.8289,
        timezone="America/Chicago",
        google_place_id="place_bishop_arts",
        hours={"monday": "6:30 AM - 7:00 PM"},
    )
    store_service.find_stores_with_product.return_value = [
        ProductAvailability(
            id=100,
            product_id=1,
            product_name="Velvet Espresso",
            product_price=16.50,
            store_id=10,
            store_name="Cymbal Coffee Bishop Arts",
            store_address="408 N Bishop Ave",
            store_city="Dallas",
            store_state="TX",
            store_zip="75208",
            latitude=32.7478,
            longitude=-96.8289,
            google_place_id="place_bishop_arts",
            stock_status="IN_STOCK",
            quantity_available=14,
            pickup_available=True,
            distance_miles=1.2,
        )
    ]

    service = GroundedRouteService(product_service=product_service, store_service=store_service)
    turn_ctx = _make_turn_context(
        user_message="Is Velvet Espresso in stock at Bishop Arts?",
        intent_detected="PRODUCT_AVAILABILITY",
        products=[
            HybridProductCandidate(
                id=1,
                name="Velvet Espresso",
                category="Whole Bean",
                price=16.50,
                description="Bold dark roast.",
                rrf_score=0.03278,
                lexical_score=90.0,
                vector_similarity=0.88,
                lexical_rank=1,
                vector_rank=1,
            )
        ],
    )

    result = await service.handle_product_availability(
        "Is Velvet Espresso in stock at Bishop Arts?",
        turn_ctx,
        location_context={"store_name": "Bishop Arts", "coordinates": {"latitude": 32.75, "longitude": -96.83}},
    )

    assert result.intent_detected == "PRODUCT_AVAILABILITY"
    assert "Velvet Espresso is available at Cymbal Coffee Bishop Arts" in result.answer
    assert "14 on hand" in result.answer
    assert len(result.inventory_results) == 1
    assert len(result.map_actions) == 2
    assert "coordinates" not in result.location_context


async def test_handle_order_status_returns_deterministic_unsupported_message() -> None:
    """ORDER_STATUS returns the deterministic unsupported-capability response."""
    service = GroundedRouteService(product_service=AsyncMock(), store_service=AsyncMock())
    turn_ctx = _make_turn_context(user_message="Where is my order #1042?", intent_detected="ORDER_STATUS")

    result = await service.handle_order_status("Where is my order #1042?", turn_ctx)

    assert result.intent_detected == "ORDER_STATUS"
    assert "does not include order tracking yet" in result.answer
    assert result.store_results == []
    assert result.inventory_results == []


async def test_telemetry_builders_produce_valid_sql_phases_and_search_metrics() -> None:
    """build_hybrid_sql_phases and build_search_metrics emit structured telemetry matching telemetry.js."""
    candidates = [
        HybridProductCandidate(
            id=1,
            name="Velvet Espresso",
            category="Whole Bean",
            price=16.50,
            description="Bold dark roast.",
            rrf_score=0.03278,
            lexical_score=90.0,
            vector_similarity=0.88,
            lexical_rank=1,
            vector_rank=1,
        )
    ]
    turn_ctx = _make_turn_context(
        user_message="Velvet Espresso", intent_detected="PRODUCT_RAG", products=candidates, term_hits={"velvet": 1}
    )

    phases = build_hybrid_sql_phases(
        query="Velvet Espresso",
        turn_context=turn_ctx,
        query_embedding=[0.01] * 3072,
        embedding_ms=11.2,
        oracle_ms=7.8,
        embedding_cache_hit=True,
        embedding_model="gemini-embedding-2",
    )
    assert all(isinstance(phase, SQLPhase) for phase in phases)
    sql_keys = [phase.sql_key for phase in phases]
    assert "get-cached-embedding" in sql_keys
    assert "hybrid-search-turn" in sql_keys
    assert "hybrid-term-hits" in sql_keys

    metrics = build_search_metrics(
        query="Velvet Espresso",
        turn_context=turn_ctx,
        total_ms=25.0,
        embedding_ms=11.2,
        oracle_ms=7.8,
        grounded_answer_mode="structured",
        grounded_answer_ms=6.0,
    )
    assert isinstance(metrics, SearchMetrics)
    assert metrics.vector_query == "Velvet Espresso"
    assert metrics.products_found == 1
    assert metrics.results_count == 1
    assert metrics.avg_similarity == pytest.approx(0.88)
    assert metrics.lexical_hits == 1

    cache_phase = build_response_cache_phase("chat:abc123", hit=True, runtime_ms=1.5)
    assert cache_phase.sql_key == "get-cached-response"
    assert cache_phase.cache_status == "hit"

    masked = safe_location_context({
        "city": "Dallas",
        "coordinates": {"latitude": 32.7, "longitude": -96.8, "accuracy_meters": 10.0},
    })
    assert masked == {"city": "Dallas", "has_browser_coordinates": True, "accuracy_meters": 10.0}

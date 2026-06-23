# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services._adk_grounding import (
    _build_map_actions,
    _compose_grounded_answer,
    _format_availability_answer,
    _ground_product_rag_turn,
    _grounded_product_answer,
)


def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the grounding module's settings at a fixed chat model."""
    settings = MagicMock()
    settings.ai.chat_model = "gemini-3.1-flash-lite"
    settings.chat.grounded_answer_timeout_seconds = 0.01
    monkeypatch.setattr("app.domain.chat.services._adk_grounding.get_settings", lambda: settings)


def _make_tools_service(
    response_text: str | None = None,
    *,
    error: Exception | None = None,
    delay_seconds: float = 0,
) -> MagicMock:
    """Build a tools-service double whose structured GenAI method returns or raises."""
    tools_service = MagicMock()

    async def generate_content(**kwargs: Any) -> Any:
        del kwargs
        if delay_seconds:
            await asyncio.sleep(delay_seconds)
        if error is not None:
            raise error
        return SimpleNamespace(text=response_text)

    tools_service.vertex_ai_service.generate_structured_content = AsyncMock(side_effect=generate_content)
    tools_service.vertex_ai_service.client.aio.models.generate_content = AsyncMock(side_effect=generate_content)
    return tools_service


def test_build_map_actions_emits_search_and_directions_per_row() -> None:
    row = {
        "name": "Cymbal Coffee Dallas Arts District",
        "address": "1717 N Harwood St",
        "city": "Dallas",
        "state": "TX",
        "zip": "75201",
        "google_place_id": "place-dallas-arts",
    }

    actions = _build_map_actions([row])

    assert len(actions) == 2
    search = next(a for a in actions if a["type"] == "search")
    directions = next(a for a in actions if a["type"] == "directions")

    assert search["label"] == "Open in Google Maps"
    assert directions["label"] == "Get directions"

    for action in (search, directions):
        assert action["url"].startswith("https://www.google.com/maps/")
        assert "api=1" in action["url"]
        assert "origin=" not in action["url"]
        assert "key=" not in action["url"]

    assert search["url"].startswith("https://www.google.com/maps/search/")
    assert directions["url"].startswith("https://www.google.com/maps/dir/")
    assert "query_place_id=place-dallas-arts" in search["url"]
    assert "destination_place_id=place-dallas-arts" in directions["url"]


def test_build_map_actions_uses_store_prefixed_field_fallbacks() -> None:
    row = {
        "store_name": "Cymbal Coffee Uptown",
        "store_address": "2000 Cedar Springs Rd",
        "store_city": "Dallas",
        "store_state": "TX",
        "store_zip": "75201",
    }

    actions = _build_map_actions([row])

    assert len(actions) == 2
    assert all("Cymbal+Coffee+Uptown" in a["url"] for a in actions)
    assert all("key=" not in a["url"] for a in actions)


def test_format_availability_no_results() -> None:
    ans = _format_availability_answer(None, [])
    assert "I couldn't find current store-level availability" in ans


def test_format_availability_target_in_stock() -> None:
    target = {
        "store_name": "Dallas Arts District",
        "product_name": "Nitro Cold Brew",
        "stock_status": "IN_STOCK",
        "quantity_available": 10,
        "distance_miles": 1.2,
    }
    ans = _format_availability_answer(target, [])
    assert ans == "Nitro Cold Brew is available at Dallas Arts District (In Stock) with 10 on hand, about 1.2 miles away."


def test_format_availability_target_low_stock() -> None:
    target = {
        "store_name": "Dallas Arts District",
        "product_name": "Nitro Cold Brew",
        "stock_status": "LOW_STOCK",
        "quantity_available": 2,
    }
    ans = _format_availability_answer(target, [])
    assert ans == "Nitro Cold Brew is available at Dallas Arts District (Low Stock) with 2 on hand."


def test_format_availability_target_out_of_stock_with_alternative() -> None:
    target = {
        "store_name": "Dallas Arts District",
        "product_name": "Nitro Cold Brew",
        "stock_status": "OUT_OF_STOCK",
        "quantity_available": 0,
    }
    alts = [
        {
            "store_name": "Dallas Uptown",
            "product_name": "Nitro Cold Brew",
            "stock_status": "IN_STOCK",
            "quantity_available": 15,
            "distance_miles": 2.5,
        }
    ]
    ans = _format_availability_answer(target, alts)
    assert ans == "Nitro Cold Brew is out of stock at Dallas Arts District. However, it is in stock at Dallas Uptown (2.5 miles away)."


def test_format_availability_target_out_of_stock_no_alternatives() -> None:
    target = {
        "store_name": "Dallas Arts District",
        "product_name": "Nitro Cold Brew",
        "stock_status": "OUT_OF_STOCK",
        "quantity_available": 0,
    }
    ans = _format_availability_answer(target, [])
    assert ans == "Nitro Cold Brew is out of stock at Dallas Arts District. I couldn't find any other stores with stock nearby."


def test_format_availability_no_target_fallback() -> None:
    alts = [
        {
            "store_name": "Dallas Uptown",
            "product_name": "Nitro Cold Brew",
            "stock_status": "IN_STOCK",
            "quantity_available": 15,
            "distance_miles": 2.5,
        },
        {
            "store_name": "Seattle",
            "product_name": "Nitro Cold Brew",
            "stock_status": "LOW_STOCK",
            "quantity_available": 5,
        }
    ]
    ans = _format_availability_answer(None, alts)
    assert ans == "Nitro Cold Brew is available at Dallas Uptown (In Stock) with 15 on hand, about 2.5 miles away. I found 2 stores with matching availability."


def test_format_availability_no_target_all_out_of_stock_uses_unavailable_wording() -> None:
    alts = [
        {
            "store_name": "Dallas Arts District",
            "product_name": "Nitro Cold Brew",
            "stock_status": "OUT_OF_STOCK",
            "quantity_available": 0,
        },
        {
            "store_name": "Dallas Uptown",
            "product_name": "Nitro Cold Brew",
            "stock_status": "OUT_OF_STOCK",
            "quantity_available": 0,
        },
    ]

    ans = _format_availability_answer(None, alts)

    assert ans == "Nitro Cold Brew is out of stock at Dallas Arts District. I couldn't find any other stores with stock nearby."
    assert "is available" not in ans


def test_grounded_product_answer_includes_store_stock_context() -> None:
    answer = _grounded_product_answer(
        "dark roast in Dallas",
        [
            {
                "id": 1,
                "name": "Midnight Brew",
                "price": 4.5,
                "description": "bold dark roast",
                "storeName": "Cymbal Coffee Dallas",
                "stockStatus": "LOW_STOCK",
                "quantityAvailable": 3,
                "pickupAvailable": True,
            }
        ],
    )

    assert "Midnight Brew ($4.50)" in answer
    assert "At Cymbal Coffee Dallas, this is low stock with 3 on hand and pickup available." in answer


@pytest.mark.anyio
async def test_ground_product_rag_turn_passes_store_id_to_fallback_search() -> None:
    tools_service = MagicMock()
    tools_service.search_products_by_vector = AsyncMock(
        return_value={
            "products": [
                {
                    "id": 1,
                    "name": "Midnight Brew",
                    "storeId": 16,
                    "storeName": "Cymbal Coffee Dallas",
                    "stockStatus": "IN_STOCK",
                }
            ],
            "results_count": 1,
        }
    )
    tools_service.vertex_ai_service.generate_structured_content = AsyncMock(side_effect=TimeoutError)
    metric_state: dict[str, Any] = {}

    answer = await _ground_product_rag_turn("dark roast", metric_state, tools_service, store_id=16)

    tools_service.search_products_by_vector.assert_awaited_once_with("dark roast", 3, 0.5, store_id=16)
    assert "Cymbal Coffee Dallas" in answer
    assert metric_state["inventory_results"][0]["storeId"] == 16


_HOUSE_BLEND = {"id": 1, "name": "House Blend", "price": 3.75, "description": "classic medium roast"}
_SUMATRA = {"id": 2, "name": "Sumatra Dark", "price": 4.0, "description": "bold and earthy"}


@pytest.mark.anyio
async def test_compose_grounded_answer_off_menu_brand_names_item(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    payload = {
        "answer": "We carry Folgers and it costs $99.",
        "mode": "off_menu_alternative",
        "off_menu_term": "Folgers",
        "selected_product_ids": ["1"],
    }
    tools_service = _make_tools_service(json.dumps(payload))

    answer = await _compose_grounded_answer("what about Folgers", [_HOUSE_BLEND, _SUMATRA], tools_service)

    assert "Cymbal Coffee does not carry Folgers" in answer
    assert "House Blend ($3.75)" in answer
    assert "$99" not in answer
    tools_service.vertex_ai_service.generate_structured_content.assert_awaited_once()
    tools_service.vertex_ai_service.client.aio.models.generate_content.assert_not_awaited()


@pytest.mark.anyio
async def test_compose_grounded_answer_preference_recommends_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    payload = {
        "answer": "Try our unsupported Moon Roast.",
        "mode": "recommend",
        "off_menu_term": "",
        "selected_product_ids": ["2"],
    }
    tools_service = _make_tools_service(json.dumps(payload))

    answer = await _compose_grounded_answer("i need something bold", [_SUMATRA], tools_service)

    assert "Sumatra Dark ($4.00)" in answer
    assert "Moon Roast" not in answer


@pytest.mark.anyio
async def test_compose_grounded_answer_hallucinated_product_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    payload = {
        "answer": "Try our Pumpkin Spice Latte!",
        "mode": "recommend",
        "off_menu_term": "",
        "selected_product_ids": ["999"],
    }
    tools_service = _make_tools_service(json.dumps(payload))

    answer = await _compose_grounded_answer("something sweet", [_HOUSE_BLEND], tools_service)

    assert "House Blend" in answer
    assert "Pumpkin Spice Latte" not in answer


@pytest.mark.anyio
async def test_compose_grounded_answer_rejects_undeclared_hallucination(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    payload = {
        "answer": "Try our Pumpkin Spice Latte!",
        "mode": "recommend",
        "off_menu_term": "",
        "selected_product_ids": ["1"],
    }
    tools_service = _make_tools_service(json.dumps(payload))

    answer = await _compose_grounded_answer("something sweet", [_HOUSE_BLEND], tools_service)

    assert "House Blend" in answer
    assert "Pumpkin Spice Latte" not in answer


@pytest.mark.anyio
async def test_compose_grounded_answer_malformed_json_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    tools_service = _make_tools_service("not valid json")

    answer = await _compose_grounded_answer("what's good", [_HOUSE_BLEND], tools_service)

    assert "House Blend" in answer


@pytest.mark.anyio
async def test_compose_grounded_answer_empty_candidates_skips_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    tools_service = _make_tools_service(error=AssertionError("LLM must not be called for empty candidates"))

    answer = await _compose_grounded_answer("what about Folgers", [], tools_service)

    assert "couldn't find a matching Cymbal Coffee menu item" in answer
    tools_service.vertex_ai_service.client.aio.models.generate_content.assert_not_awaited()


@pytest.mark.anyio
async def test_compose_grounded_answer_non_credential_error_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    tools_service = _make_tools_service(error=RuntimeError("temporary network blip"))

    answer = await _compose_grounded_answer("what's good", [_HOUSE_BLEND], tools_service)

    assert "House Blend" in answer


@pytest.mark.anyio
async def test_compose_grounded_answer_credential_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    tools_service = _make_tools_service(error=RuntimeError("API key not valid. Please pass a valid API key."))

    with pytest.raises(AIServiceUnconfigured):
        await _compose_grounded_answer("what's good", [_HOUSE_BLEND], tools_service)


@pytest.mark.anyio
async def test_compose_grounded_answer_timeout_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    payload = {
        "answer": "Try our unsupported Moon Roast.",
        "mode": "recommend",
        "off_menu_term": "",
        "selected_product_ids": ["1"],
    }
    tools_service = _make_tools_service(json.dumps(payload), delay_seconds=0.05)

    answer = await _compose_grounded_answer("what's good", [_HOUSE_BLEND], tools_service)

    assert "House Blend" in answer
    assert "Moon Roast" not in answer

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from app.domain.chat.services._adk_grounding import _build_map_actions, _format_availability_answer


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

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from app.domain.chat.services._adk_grounding import _format_availability_answer


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

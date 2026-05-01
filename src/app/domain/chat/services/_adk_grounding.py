# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Private grounding, routing, and map-formatting helpers for ADK chat."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode, urlunsplit

from app.domain.chat.services._adk_telemetry import _coerce_sql_phases

_KNOWN_CITY_FILTERS: tuple[tuple[str, str | None], ...] = (
    ("Austin", "TX"),
    ("Berkeley", "CA"),
    ("Dallas", "TX"),
    ("Denver", "CO"),
    ("Fresno", "CA"),
    ("Los Angeles", "CA"),
    ("Oakland", "CA"),
    ("Palo Alto", "CA"),
    ("Portland", "OR"),
    ("Sacramento", "CA"),
    ("San Diego", "CA"),
    ("San Francisco", "CA"),
    ("San Jose", "CA"),
    ("Santa Monica", "CA"),
    ("Seattle", "WA"),
)
_PRODUCT_QUERY_ALIASES: tuple[tuple[str, str], ...] = (
    ("cold brew", "Cold Brew Nitro"),
    ("nitro", "Cold Brew Nitro"),
    ("espresso", "Espresso Romano"),
)
_MIN_LATITUDE = -90.0
_MAX_LATITUDE = 90.0
_MIN_LONGITUDE = -180.0
_MAX_LONGITUDE = 180.0


def _coerce_products(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict) and item.get("name")]


def _format_price(value: Any) -> str:
    if not isinstance(value, int | float):
        return ""
    return f" (${value:.2f})"


def _grounded_product_answer(query: str, products: list[dict[str, Any]]) -> str:
    menu_products = _coerce_products(products)
    if not menu_products:
        return "I couldn't find a matching Cymbal Coffee menu item for that. Try another flavor, roast, or drink style and I'll check the menu again."

    first = menu_products[0]
    lead = "For breakfast" if "breakfast" in query.casefold() else "For that"
    name = str(first["name"])
    description = str(first.get("description") or "").strip()
    answer = f"{lead}, I'd start with {name}{_format_price(first.get('price'))}"
    if description:
        answer += f": {description}"
    else:
        answer += "."

    if len(menu_products) > 1:
        second = menu_products[1]
        answer += f" Another good menu option is {second['name']}{_format_price(second.get('price'))}."
    return answer


def _coerce_dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _default_route_fields(location_context: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "store_results": [],
        "inventory_results": [],
        "map_actions": [],
        "location_context": _safe_location_context(location_context),
    }


def _safe_location_context(location_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(location_context, dict):
        return {}

    safe: dict[str, Any] = {}
    for key in ("city", "state", "zip_code", "store_name"):
        value = location_context.get(key)
        if value:
            safe[key] = str(value)

    coordinates = location_context.get("coordinates")
    if isinstance(coordinates, dict) and _request_coordinates(location_context):
        safe["has_browser_coordinates"] = True
        accuracy = coordinates.get("accuracy_meters")
        if isinstance(accuracy, int | float):
            safe["accuracy_meters"] = float(accuracy)
    return safe


def _request_coordinates(location_context: dict[str, Any] | None) -> tuple[float, float] | None:
    if not isinstance(location_context, dict):
        return None
    coordinates = location_context.get("coordinates")
    if not isinstance(coordinates, dict):
        return None
    latitude = coordinates.get("latitude")
    longitude = coordinates.get("longitude")
    if not isinstance(latitude, int | float) or not isinstance(longitude, int | float):
        return None
    if not _MIN_LATITUDE <= float(latitude) <= _MAX_LATITUDE or not (
        _MIN_LONGITUDE <= float(longitude) <= _MAX_LONGITUDE
    ):
        return None
    return float(latitude), float(longitude)


def _has_browser_coordinates(location_context: dict[str, Any] | None) -> bool:
    return _request_coordinates(location_context) is not None


def _extract_location_filters(query: str, location_context: dict[str, Any] | None) -> dict[str, str | None]:
    context = location_context if isinstance(location_context, dict) else {}
    filters: dict[str, str | None] = {
        "city": str(context.get("city") or "").strip() or None,
        "state": str(context.get("state") or "").strip() or None,
        "zip_code": str(context.get("zip_code") or "").strip() or None,
    }
    query_text = query.casefold()
    if not filters["zip_code"]:
        zip_match = re.search(r"\b\d{5}(?:-\d{4})?\b", query)
        if zip_match:
            filters["zip_code"] = zip_match.group(0)
    if not filters["city"]:
        for city, _state in _KNOWN_CITY_FILTERS:
            if city.casefold() in query_text:
                filters["city"] = city
                break
    return filters


def _extract_product_query(query: str) -> str:
    query_text = query.casefold()
    for needle, product_name in _PRODUCT_QUERY_ALIASES:
        if needle in query_text:
            return product_name

    cleaned = re.sub(
        r"\b(where|can|i|pick|up|near|me|is|are|available|availability|which|cafe|store|has|have|in|at|do|you|the|a|an)\b",
        " ",
        query_text,
    )
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned.title() if cleaned else query


def _store_query_parts(row: dict[str, Any]) -> tuple[str, str]:
    name = str(row.get("name") or row.get("store_name") or "Cymbal Coffee").strip()
    address = str(row.get("address") or row.get("store_address") or "").strip()
    city = str(row.get("city") or row.get("store_city") or "").strip()
    state = str(row.get("state") or row.get("store_state") or "").strip()
    zip_code = str(row.get("zip") or row.get("store_zip") or "").strip()
    locality = " ".join(part for part in (state, zip_code) if part)
    city_region = ", ".join(part for part in (city, locality) if part)
    query = ", ".join(part for part in (name, address, city_region) if part)
    return name, query or name


def _maps_search_url(query: str, place_id: str | None = None) -> str:
    params = {"api": "1", "query": query}
    if place_id:
        params["query_place_id"] = place_id
    return urlunsplit(("https", "www.google.com", "/maps/search/", urlencode(params), ""))


def _build_map_actions(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for row in rows:
        label, query = _store_query_parts(row)
        actions.append(
            {
                "type": "search",
                "label": label,
                "url": _maps_search_url(query, str(row.get("google_place_id") or "") or None),
            }
        )
    return actions


def _format_hours(hours: Any) -> str:
    if not isinstance(hours, dict) or not hours:
        return ""
    monday = hours.get("monday")
    if monday:
        return f" Hours: Monday {monday}."
    first_key, first_value = next(iter(hours.items()))
    return f" Hours: {str(first_key).title()} {first_value}."


def _format_store_location_answer(stores: list[dict[str, Any]]) -> str:
    if not stores:
        return "I couldn't find a matching Cymbal Coffee store for that location. Try a city, ZIP code, or nearby landmark."

    first = stores[0]
    name, _query = _store_query_parts(first)
    address = str(first.get("address") or "").strip()
    city = str(first.get("city") or "").strip()
    state = str(first.get("state") or "").strip()
    zip_code = str(first.get("zip") or "").strip()
    phone = str(first.get("phone") or "").strip()
    location = ", ".join(part for part in (address, city, " ".join(part for part in (state, zip_code) if part)) if part)
    answer = f"{name}"
    if location:
        answer += f" is at {location}."
    else:
        answer += " is the closest matching Cymbal Coffee location."
    if phone:
        answer += f" Phone: {phone}."
    answer += _format_hours(first.get("hours"))
    if len(stores) > 1:
        answer += f" I found {len(stores)} matching stores."
    return answer


def _format_availability_answer(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "I couldn't find current store-level availability for that product. Try another menu item or nearby location."

    first = rows[0]
    product = str(first.get("product_name") or "that item")
    store = str(first.get("store_name") or "a Cymbal Coffee store")
    status = str(first.get("stock_status") or "").replace("_", " ").title()
    quantity = first.get("quantity_available")
    answer = f"{product} is available at {store}"
    if status:
        answer += f" ({status})"
    if isinstance(quantity, int | float):
        answer += f" with {int(quantity)} on hand"
    distance = first.get("distance_miles")
    if isinstance(distance, int | float):
        answer += f", about {float(distance):.1f} miles away"
    answer += "."
    if len(rows) > 1:
        answer += f" I found {len(rows)} stores with matching availability."
    return answer


def _record_product_search_result(metric_state: dict[str, Any], result: dict[str, Any], query: str) -> None:
    metric_state["embedding_cache_hit"] = bool(result.get("embedding_cache_hit"))
    products = _coerce_products(result.get("products"))
    if products:
        metric_state["rag_products"] = products
    products_found = int(result.get("results_count") or len(products))
    search_metrics = metric_state.setdefault("search_metrics", {})
    tool_metrics = result.get("search_metrics")
    if isinstance(tool_metrics, dict):
        search_metrics.update(tool_metrics)
    search_metrics["vector_query"] = str(result.get("vector_query") or query)
    search_metrics["results_count"] = products_found
    search_metrics["products_found"] = products_found
    sql_phases = _coerce_sql_phases(result.get("sql_phases"))
    if sql_phases:
        metric_state.setdefault("sql_phases", []).extend(sql_phases)


async def _ground_product_rag_turn(
    query: str,
    metric_state: dict[str, Any],
    tools_service: Any,
) -> str:
    products = _coerce_products(metric_state.get("rag_products"))
    if not products:
        fallback_result = await tools_service.search_products_by_vector(query, 3, 0.5)
        _record_product_search_result(metric_state, fallback_result, query)
        products = _coerce_products(metric_state.get("rag_products"))
    return _grounded_product_answer(query, products)

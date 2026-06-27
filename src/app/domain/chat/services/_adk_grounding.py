# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Private grounding, routing, and map-formatting helpers for ADK chat."""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, TypedDict

import structlog
from google.genai import types

from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services._adk_support import _coerce_sql_phases
from app.domain.products.services.maps import build_store_directions_url, build_store_search_url
from app.domain.system.services import PersonaManager
from app.lib.settings import get_settings

logger = structlog.get_logger()


class _StoreFields(TypedDict):
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    place_id: str | None


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
_PRODUCT_QUERY_STOP_WORDS = frozenset({
    "where",
    "can",
    "i",
    "pick",
    "up",
    "near",
    "me",
    "is",
    "are",
    "available",
    "availability",
    "which",
    "cafe",
    "store",
    "has",
    "have",
    "in",
    "at",
    "do",
    "you",
    "the",
    "a",
    "an",
    "that",
    "this",
    "it",
    "them",
    "those",
    "stock",
    "nearby",
    "here",
    "there",
})
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
    stock_sentence = _format_product_match_stock_sentence(first)
    if stock_sentence:
        answer += f" {stock_sentence}"

    if len(menu_products) > 1:
        second = menu_products[1]
        answer += f" Another good menu option is {second['name']}{_format_price(second.get('price'))}."
    return answer


def _format_product_match_stock_sentence(product: dict[str, Any]) -> str:
    store_name = _get_field(product, "store_name")
    status = _get_field(product, "stock_status")
    if not store_name or not status:
        return ""
    status_str = str(status).replace("_", " ").title()
    answer = f"At {store_name}, this is {status_str.lower()}"
    quantity = _get_field(product, "quantity_available")
    if isinstance(quantity, int | float):
        answer += f" with {int(quantity)} on hand"
    pickup_available = _get_field(product, "pickup_available")
    if pickup_available is True:
        answer += " and pickup available"
    elif pickup_available is False:
        answer += " and pickup unavailable"
    return answer + "."


_GROUNDED_ANSWER_TEMPERATURE = 0
_GROUNDED_SELECTION_MODES = frozenset({"recommend", "off_menu_alternative"})
_GROUNDED_ANSWER_INSTRUCTION_TEMPLATE = """You are a Cymbal Coffee product selector acting under a specific Barista Persona.
Choose from ONLY the candidate products provided.

Persona Guidelines:
{persona_guidelines}

Rules:
- Do NOT write the final customer response.
- Return product ids from the candidate list only.
- Use mode "off_menu_alternative" only when the customer names a specific brand or product Cymbal Coffee does not carry, such as Folgers or Starbucks.
- Use mode "recommend" for preferences such as "something bold", "for breakfast", or "what should I get".
- Never invent products, ids, prices, descriptions, or availability.
- Provide a short 1-sentence "explanation" explaining why this selection fits the customer request from your persona's perspective. Keep it in character and match your persona's tone.

Respond as JSON: mode, selected_product_ids, off_menu_term, explanation."""

_GROUNDED_ANSWER_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "mode": {"type": "STRING", "enum": sorted(_GROUNDED_SELECTION_MODES)},
        "selected_product_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
        "off_menu_term": {"type": "STRING"},
        "explanation": {"type": "STRING"},
    },
    "required": ["mode", "selected_product_ids", "off_menu_term", "explanation"],
}


def _candidate_id(product: dict[str, Any]) -> str:
    for key in ("id", "product_id", "sku", "name"):
        value = product.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return str(product["name"]).strip()


def _candidate_block(products: list[dict[str, Any]]) -> str:
    """Render candidate products as the only menu items the model may select.

    Returns:
        A newline-delimited list of id/name/price/description rows.
    """
    lines: list[str] = []
    for product in products:
        name = str(product.get("name") or "").strip()
        if not name:
            continue
        description = str(product.get("description") or "").strip()
        line = f"- id={_candidate_id(product)}; name={name}{_format_price(product.get('price'))}"
        if description:
            line += f"; description={description}"
        lines.append(line)
    return "\n".join(lines)


def _response_payload(response: Any) -> dict[str, Any] | None:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, dict):
        return parsed
    text = getattr(response, "text", "")
    try:
        payload = json.loads(str(text))
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _selected_products(payload: dict[str, Any], products: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    mode = str(payload.get("mode") or "").strip()
    if mode not in _GROUNDED_SELECTION_MODES:
        return None
    selected_ids = payload.get("selected_product_ids")
    if not isinstance(selected_ids, list) or not selected_ids:
        return None

    candidates = {_candidate_id(product): product for product in products}
    selected: list[dict[str, Any]] = []
    for raw_id in selected_ids:
        product = candidates.get(str(raw_id).strip())
        if product is None:
            return None
        selected.append(product)
    return selected


def _clean_off_menu_term(value: Any) -> str:
    term = re.sub(r"\s+", " ", str(value or "").strip().strip("\"'"))
    return term[:60] or "that item"


def _render_selected_product(product: dict[str, Any]) -> str:
    name = str(product["name"])
    return f"{name}{_format_price(product.get('price'))}"


def _render_grounded_selection(query: str, payload: dict[str, Any], selected: list[dict[str, Any]]) -> str | None:
    """Render final copy from trusted candidate rows, never from model text.

    Returns:
        Customer-facing answer text when the structured selection is valid.
    """
    mode = str(payload.get("mode") or "").strip()
    explanation = str(payload.get("explanation") or "").strip()

    if mode == "recommend":
        base_answer = _grounded_product_answer(query, selected)
        if explanation:
            return f"{explanation} {base_answer}"
        return base_answer

    if mode == "off_menu_alternative":
        first = selected[0]
        answer = (
            f"Cymbal Coffee does not carry {_clean_off_menu_term(payload.get('off_menu_term'))}, "
            f"but {_render_selected_product(first)} is the closest menu option"
        )
        description = str(first.get("description") or "").strip()
        if description:
            answer += f": {description}"
        answer += "."
        if explanation:
            return f"{explanation} {answer}"
        return answer
    return None


def _record_grounded_answer_metric(
    metric_state: dict[str, Any] | None, *, mode: str, started: float, error_type: str | None = None
) -> None:
    if metric_state is None:
        return
    search_metrics = metric_state.setdefault("search_metrics", {})
    search_metrics["grounded_answer_mode"] = mode
    search_metrics["grounded_answer_ms"] = round((time.perf_counter() - started) * 1000, 2)
    if error_type:
        search_metrics["grounded_answer_error_type"] = error_type


async def _compose_grounded_answer(
    query: str,
    products: list[dict[str, Any]],
    tools_service: Any,
    metric_state: dict[str, Any] | None = None,
    persona: str = "barista",
) -> str:
    """Select with the LLM, then render the customer reply from trusted rows.

    The model never writes final product copy. It may only return candidate ids
    and an off-menu term; Python validates those ids and renders names, prices,
    and descriptions from the retrieved products.

    Returns:
        The grounded reply text, or the templated answer when composition fails.

    Raises:
        AIServiceUnconfigured: If the configured Vertex AI credentials are invalid.
    """
    menu_products = _coerce_products(products)
    started = time.perf_counter()
    if not menu_products:
        _record_grounded_answer_metric(metric_state, mode="template", started=started)
        return _grounded_product_answer(query, menu_products)

    contents = (
        f"Customer request: {query}\n\nCandidate products (select only these ids):\n{_candidate_block(menu_products)}"
    )
    persona_config = PersonaManager.PERSONAS.get(persona, PersonaManager.PERSONAS["barista"])
    instruction = _GROUNDED_ANSWER_INSTRUCTION_TEMPLATE.format(persona_guidelines=persona_config.system_prompt_addon)
    try:
        async with asyncio.timeout(get_settings().chat.grounded_answer_timeout_seconds):
            response = await tools_service.vertex_ai_service.generate_structured_content(
                model=get_settings().ai.chat_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=_GROUNDED_ANSWER_TEMPERATURE,
                    system_instruction=instruction,
                    response_mime_type="application/json",
                    response_schema=_GROUNDED_ANSWER_SCHEMA,
                ),
            )
    except TimeoutError:
        _record_grounded_answer_metric(metric_state, mode="timeout", started=started, error_type="TimeoutError")
        await logger.awarning("Grounded answer generation timed out")
        return _grounded_product_answer(query, menu_products)
    except Exception as exc:
        # Lazy import avoids an import cycle: adk.py imports this module at load time.
        from app.domain.chat.services.adk import _UNCONFIGURED_MESSAGE, _is_credential_error

        if _is_credential_error(exc):
            raise AIServiceUnconfigured(_UNCONFIGURED_MESSAGE) from exc
        _record_grounded_answer_metric(metric_state, mode="error", started=started, error_type=type(exc).__name__)
        await logger.awarning("Grounded answer generation failed", error_type=type(exc).__name__)
        return _grounded_product_answer(query, menu_products)

    payload = _response_payload(response)
    selected = _selected_products(payload, menu_products) if payload is not None else None
    answer = (
        _render_grounded_selection(query, payload, selected) if payload is not None and selected is not None else None
    )
    if answer is None:
        _record_grounded_answer_metric(metric_state, mode="rejected", started=started)
        await logger.awarning("Grounded answer rejected by guard")
        return _grounded_product_answer(query, menu_products)
    _record_grounded_answer_metric(metric_state, mode="structured", started=started)
    return answer


def _coerce_dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _get_field(row: dict[str, Any], snake_name: str) -> Any:
    if snake_name in row:
        return row[snake_name]
    parts = snake_name.split("_")
    camel_name = parts[0] + "".join(p.title() for p in parts[1:])
    return row.get(camel_name)


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


def _extract_product_query(query: str) -> str | None:
    query_text = query.casefold()
    for needle, product_name in _PRODUCT_QUERY_ALIASES:
        if needle in query_text:
            return product_name

    cleaned = re.sub(r"[^a-z0-9 ]+", " ", query_text)
    words = [word for word in cleaned.split() if word not in _PRODUCT_QUERY_STOP_WORDS]
    cleaned = " ".join(words)
    return cleaned.title() if cleaned else None


def _store_name(row: dict[str, Any]) -> str:
    return str(row.get("name") or row.get("store_name") or "Cymbal Coffee").strip() or "Cymbal Coffee"


def _store_fields(row: dict[str, Any]) -> _StoreFields:
    return {
        "name": _store_name(row),
        "address": str(row.get("address") or row.get("store_address") or "").strip(),
        "city": str(row.get("city") or row.get("store_city") or "").strip(),
        "state": str(row.get("state") or row.get("store_state") or "").strip(),
        "zip_code": str(row.get("zip") or row.get("store_zip") or "").strip(),
        "place_id": str(row.get("google_place_id") or "") or None,
    }


def _build_map_actions(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for row in rows:
        fields = _store_fields(row)
        actions.extend((
            {"type": "search", "label": "Open in Google Maps", "url": build_store_search_url(**fields)},
            {"type": "directions", "label": "Get directions", "url": build_store_directions_url(**fields)},
        ))
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
    name = _store_name(first)
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


def _is_in_stock(row: dict[str, Any]) -> bool:
    status = _get_field(row, "stock_status")
    qty = _get_field(row, "quantity_available")
    if status in {"IN_STOCK", "LOW_STOCK"}:
        return True
    return bool(isinstance(qty, int | float) and qty > 0)


def _format_in_stock_store(product_name: str, store_name: str, quantity: Any, status: str | None, distance: Any) -> str:
    status_str = str(status or "").replace("_", " ").title()
    answer = f"{product_name} is available at {store_name}"
    if status_str:
        answer += f" ({status_str})"
    if isinstance(quantity, int | float):
        answer += f" with {int(quantity)} on hand"
    if isinstance(distance, int | float):
        answer += f", about {float(distance):.1f} miles away"
    answer += "."
    return answer


def _format_out_of_stock_store(product_name: str, store_name: str, alternatives: list[dict[str, Any]]) -> str:
    answer = f"{product_name} is out of stock at {store_name}."
    in_stock_alts = [alt for alt in alternatives if _is_in_stock(alt)]
    if in_stock_alts:
        best_alt = in_stock_alts[0]
        alt_name = _get_field(best_alt, "store_name")
        alt_distance = _get_field(best_alt, "distance_miles")
        answer += f" However, it is in stock at {alt_name}"
        if isinstance(alt_distance, int | float):
            answer += f" ({float(alt_distance):.1f} miles away)"
        answer += "."
    else:
        answer += " I couldn't find any other stores with stock nearby."
    return answer


def _format_availability_answer(
    target: dict[str, Any] | None, alternatives: list[dict[str, Any]], target_store_name: str | None = None
) -> str:
    if not target and not alternatives:
        return "I couldn't find current store-level availability for that product. Try another menu item or nearby location."

    product_name: str | None = None
    if target:
        product_name = str(_get_field(target, "product_name") or "")
    elif alternatives:
        product_name = str(_get_field(alternatives[0], "product_name") or "")
    if not product_name:
        product_name = "that item"

    if target or target_store_name:
        store_name = str((_get_field(target, "store_name") if target else target_store_name) or "a Cymbal Coffee store")
        if target and _is_in_stock(target):
            return _format_in_stock_store(
                product_name=product_name,
                store_name=store_name,
                quantity=_get_field(target, "quantity_available"),
                status=_get_field(target, "stock_status"),
                distance=_get_field(target, "distance_miles"),
            )
        return _format_out_of_stock_store(product_name=product_name, store_name=store_name, alternatives=alternatives)

    available_alternatives = [alt for alt in alternatives if _is_in_stock(alt)]
    if not available_alternatives:
        first = alternatives[0]
        store_name = str(_get_field(first, "store_name") or "a Cymbal Coffee store")
        return _format_out_of_stock_store(product_name=product_name, store_name=store_name, alternatives=[])

    first = available_alternatives[0]
    store_name = _get_field(first, "store_name") or "a Cymbal Coffee store"
    in_stock_sentence = _format_in_stock_store(
        product_name=product_name,
        store_name=store_name,
        quantity=_get_field(first, "quantity_available"),
        status=_get_field(first, "stock_status"),
        distance=_get_field(first, "distance_miles"),
    )
    if len(available_alternatives) <= 1:
        return in_stock_sentence
    # The in-stock sentence ends with a period; replace it with a follow-on clause.
    base_sentence = in_stock_sentence.removesuffix(".")
    found_clause = f". I found {len(available_alternatives)} stores with matching availability."
    return base_sentence + found_clause


def _record_product_search_result(metric_state: dict[str, Any], result: dict[str, Any], query: str) -> None:
    metric_state["embedding_cache_hit"] = bool(result.get("embedding_cache_hit"))
    products = _coerce_products(result.get("products"))
    if products:
        metric_state["rag_products"] = products
        inventory_products = [product for product in products if _get_field(product, "store_id") is not None]
        if inventory_products:
            metric_state["inventory_results"] = inventory_products
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
    *,
    store_id: int | None = None,
    persona: str = "barista",
) -> str:
    products = _coerce_products(metric_state.get("rag_products"))
    if store_id is not None and not any(_get_field(product, "store_id") == store_id for product in products):
        products = []
    if not products:
        fallback_result = await tools_service.search_products_by_vector(query, 3, 0.5, store_id=store_id)
        _record_product_search_result(metric_state, fallback_result, query)
        products = _coerce_products(metric_state.get("rag_products"))
    return await _compose_grounded_answer(query, products, tools_service, metric_state, persona=persona)

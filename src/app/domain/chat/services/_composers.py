# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Deterministic response composers for grounded chat routes."""

from __future__ import annotations

import re
from typing import Any

__all__ = (
    "ORDER_STATUS_ANSWER",
    "build_candidate_block",
    "compose_availability_answer",
    "compose_grounded_selection",
    "compose_off_menu_alternative",
    "compose_product_rag_answer",
    "compose_store_location_answer",
    "partition_availability_rows",
    "select_grounded_products",
)

ORDER_STATUS_ANSWER = (
    "This demo does not include order tracking yet. I can help with menu recommendations, "
    "store locations, and product availability."
)


def compose_off_menu_alternative(off_menu_term: str, products: list[dict[str, Any]]) -> str:
    """Compose a deterministic response when a customer asks for an off-menu brand or item."""
    cleaned_term = re.sub(r"\s+", " ", off_menu_term.strip().strip("\"'"))[:60] or "that item"
    if not products:
        return (
            f"Cymbal Coffee does not carry {cleaned_term}. "
            "Ask about our light, medium, or dark roasts and I can recommend an in-catalog option."
        )
    first = products[0]
    answer = (
        f"Cymbal Coffee does not carry {cleaned_term}, but {_render_selected_product(first)} is the closest menu option"
    )
    description = str(first.get("description") or "").strip()
    if description:
        answer += f": {description}"
    if not answer.endswith("."):
        answer += "."
    if len(products) > 1:
        second = products[1]
        answer += f" Another good menu option is {_render_selected_product(second)}."
    return answer


def compose_product_rag_answer(query: str, products: list[dict[str, Any]]) -> str:
    """Compose a deterministic recommendation sentence from ranked catalog candidates."""
    if not products:
        return (
            "I couldn't find a matching Cymbal Coffee menu item for that. "
            "Try another flavor, roast, or drink style and I'll check the menu again."
        )
    first = products[0]
    lead = "For breakfast" if "breakfast" in query.casefold() else "For that"
    name = str(first["name"])
    description = str(first.get("description") or "").strip()
    answer = f"{lead}, I'd start with {name}{_format_price(first.get('price'))}"
    if description:
        answer += f": {description}"
    if not answer.endswith("."):
        answer += "."
    if len(products) > 1:
        second = products[1]
        answer += f" Another good menu option is {second['name']}{_format_price(second.get('price'))}."
    return answer


def build_candidate_block(products: list[dict[str, Any]]) -> str:
    """Format ranked product dictionaries into a bulleted prompt candidate block."""
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


def select_grounded_products(
    payload: dict[str, Any], products: list[dict[str, Any]], *, allowed_modes: frozenset[str]
) -> list[dict[str, Any]] | None:
    """Validate and resolve model-selected product IDs strictly against candidate products."""
    mode = str(payload.get("mode") or "").strip()
    if mode not in allowed_modes:
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


def compose_grounded_selection(query: str, payload: dict[str, Any], selected: list[dict[str, Any]]) -> str | None:
    """Render a validated structured product selection with its persona explanation."""
    mode = str(payload.get("mode") or "").strip()
    explanation = str(payload.get("explanation") or "").strip()
    if mode == "recommend":
        base_answer = compose_product_rag_answer(query, selected)
        return f"{explanation} {base_answer}" if explanation else base_answer
    if mode == "off_menu_alternative":
        off_menu_term = str(payload.get("off_menu_term") or "that item")
        answer = compose_off_menu_alternative(off_menu_term, selected)
        return f"{explanation} {answer}" if explanation else answer
    return None


def compose_store_location_answer(stores: list[dict[str, Any]]) -> str:
    """Compose a deterministic store location summary from matched store rows."""
    if not stores:
        return (
            "I couldn't find a matching Cymbal Coffee store for that location. "
            "Try a city, ZIP code, or nearby landmark."
        )
    first = stores[0]
    name = str(first.get("name") or first.get("store_name") or "Cymbal Coffee").strip() or "Cymbal Coffee"
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


def partition_availability_rows(
    inventory: list[dict[str, Any]], target_store_id: int | None
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Split inventory rows into an optional target store match and remaining alternative stores."""
    if target_store_id is None:
        return None, inventory
    target_row: dict[str, Any] | None = None
    alternatives: list[dict[str, Any]] = []
    for row in inventory:
        if _get_field(row, "store_id") == target_store_id:
            target_row = row
        else:
            alternatives.append(row)
    if target_row is None:
        return None, inventory
    return target_row, alternatives


def compose_availability_answer(
    *, target: dict[str, Any] | None, alternatives: list[dict[str, Any]], target_store_name: str | None = None
) -> str:
    """Compose a deterministic product availability summary across target and nearby stores."""
    if not target and not alternatives:
        return (
            "I couldn't find current store-level availability for that product. "
            "Try another menu item or nearby location."
        )

    product_name = _resolve_inventory_product_name(target, alternatives)
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
    store_name = str(_get_field(first, "store_name") or "a Cymbal Coffee store")
    in_stock_sentence = _format_in_stock_store(
        product_name=product_name,
        store_name=store_name,
        quantity=_get_field(first, "quantity_available"),
        status=_get_field(first, "stock_status"),
        distance=_get_field(first, "distance_miles"),
    )
    if len(available_alternatives) <= 1:
        return in_stock_sentence
    base_sentence = in_stock_sentence.removesuffix(".")
    return f"{base_sentence}. I found {len(available_alternatives)} stores with matching availability."


def _resolve_inventory_product_name(target: dict[str, Any] | None, alternatives: list[dict[str, Any]]) -> str:
    """Resolve the display product name from target or fallback availability rows."""
    if target:
        name = str(_get_field(target, "product_name") or "")
        if name:
            return name
    if alternatives:
        name = str(_get_field(alternatives[0], "product_name") or "")
        if name:
            return name
    return "that item"


def _get_field(row: dict[str, Any], snake_name: str) -> Any:
    """Look up a field in either snake_case or camelCase dictionary representations."""
    if snake_name in row:
        return row[snake_name]
    parts = snake_name.split("_")
    camel_name = parts[0] + "".join(p.title() for p in parts[1:])
    return row.get(camel_name)


def _format_price(value: Any) -> str:
    """Format numeric price values as `` ($X.XX)`` suffixes."""
    if not isinstance(value, int | float):
        return ""
    return f" (${value:.2f})"


def _render_selected_product(product: dict[str, Any]) -> str:
    """Format a product name with its optional price suffix."""
    name = str(product["name"])
    return f"{name}{_format_price(product.get('price'))}"


def _candidate_id(product: dict[str, Any]) -> str:
    """Extract a stable string identifier for candidate validation."""
    for key in ("id", "product_id", "sku", "name"):
        value = product.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return str(product["name"]).strip()


def _format_hours(hours: Any) -> str:
    """Render a concise store hours clause when hours metadata is present."""
    if not isinstance(hours, dict) or not hours:
        return ""
    monday = hours.get("monday")
    if monday:
        return f" Hours: Monday {monday}."
    first_key, first_value = next(iter(hours.items()))
    return f" Hours: {str(first_key).title()} {first_value}."


def _is_in_stock(row: dict[str, Any]) -> bool:
    """Return True when an inventory row indicates available stock."""
    status = _get_field(row, "stock_status")
    qty = _get_field(row, "quantity_available")
    if status in {"IN_STOCK", "LOW_STOCK"}:
        return True
    return bool(isinstance(qty, int | float) and qty > 0)


def _format_in_stock_store(product_name: str, store_name: str, quantity: Any, status: str | None, distance: Any) -> str:
    """Format an in-stock availability sentence for a single store."""
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
    """Format an out-of-stock sentence with an optional nearby in-stock alternative."""
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

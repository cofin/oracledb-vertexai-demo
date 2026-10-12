# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Deterministic grounded route composers for Cymbal Coffee chat turns."""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import TYPE_CHECKING, Any

import msgspec
import structlog
from google.genai import errors as genai_errors
from google.genai import types

from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services._telemetry import (
    SearchMetrics,
    SQLPhase,
    build_hybrid_sql_phases,
    build_map_actions,
    build_search_metrics,
    build_sql_phase,
    extract_location_filters,
    extract_product_query,
    request_coordinates,
    safe_location_context,
)
from app.domain.system.services import PersonaManager
from app.lib.settings import get_settings
from app.utils.serialization import sanitize_for_json

if TYPE_CHECKING:
    from app.domain.chat.schemas import HybridProductCandidate, HybridRouteLabel, HybridTurnContext
    from app.domain.products.services import ProductService, StoreService, VertexAIService

logger = structlog.get_logger()

_UNCONFIGURED_MESSAGE = "AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file."
_ORDER_STATUS_ANSWER = (
    "This demo does not include order tracking yet. I can help with menu recommendations, "
    "store locations, and product availability."
)
_GROUNDED_ANSWER_TEMPERATURE = 0.0
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


class GroundedTurnResult(msgspec.Struct, kw_only=True):
    """Completed deterministic turn payload ready for caching and SSE emission."""

    answer: str
    intent_detected: HybridRouteLabel
    search_metrics: SearchMetrics
    sql_phases: list[SQLPhase]
    embedding_cache_hit: bool = False
    store_results: list[dict[str, Any]] = []
    inventory_results: list[dict[str, Any]] = []
    map_actions: list[dict[str, str]] = []
    location_context: dict[str, Any] = {}
    last_products: list[str] | None = None


class GroundedRouteService:
    """Composes deterministic responses for PRODUCT_RAG, STORE_LOCATION, PRODUCT_AVAILABILITY, and ORDER_STATUS."""

    def __init__(
        self,
        *,
        product_service: ProductService,
        store_service: StoreService,
        vertex_ai_service: VertexAIService | None = None,
    ) -> None:
        self.product_service = product_service
        self.store_service = store_service
        self.vertex_ai_service = vertex_ai_service

    async def dispatch(
        self,
        query: str,
        turn_context: HybridTurnContext,
        *,
        location_context: dict[str, Any] | None = None,
        persona: str = "barista",
        last_products: list[str] | None = None,
        embedding_ms: float = 0.0,
        oracle_ms: float = 0.0,
        embedding_cache_hit: bool = False,
        query_embedding: list[float] | None = None,
    ) -> GroundedTurnResult | None:
        """Dispatch deterministic intents to their grounded handler, or return None for agent turns."""
        if not turn_context.is_deterministic:
            return None
        if turn_context.intent_detected == "PRODUCT_RAG":
            return await self.handle_product_rag(
                query,
                turn_context,
                location_context=location_context,
                persona=persona,
                embedding_ms=embedding_ms,
                oracle_ms=oracle_ms,
                embedding_cache_hit=embedding_cache_hit,
                query_embedding=query_embedding,
            )
        if turn_context.intent_detected == "STORE_LOCATION":
            return await self.handle_store_location(
                query,
                turn_context,
                location_context=location_context,
                embedding_ms=embedding_ms,
                oracle_ms=oracle_ms,
                embedding_cache_hit=embedding_cache_hit,
                query_embedding=query_embedding,
            )
        if turn_context.intent_detected == "PRODUCT_AVAILABILITY":
            return await self.handle_product_availability(
                query,
                turn_context,
                location_context=location_context,
                last_products=last_products,
                embedding_ms=embedding_ms,
                oracle_ms=oracle_ms,
                embedding_cache_hit=embedding_cache_hit,
                query_embedding=query_embedding,
            )
        if turn_context.intent_detected == "ORDER_STATUS":
            return await self.handle_order_status(
                query,
                turn_context,
                location_context=location_context,
                embedding_ms=embedding_ms,
                oracle_ms=oracle_ms,
                embedding_cache_hit=embedding_cache_hit,
                query_embedding=query_embedding,
            )
        return None

    async def handle_product_rag(
        self,
        query: str,
        turn_context: HybridTurnContext,
        *,
        location_context: dict[str, Any] | None = None,
        persona: str = "barista",
        embedding_ms: float = 0.0,
        oracle_ms: float = 0.0,
        embedding_cache_hit: bool = False,
        query_embedding: list[float] | None = None,
    ) -> GroundedTurnResult:
        """Compose a grounded product recommendation or deterministic off-menu alternative."""
        started = time.perf_counter()
        products = _candidates_to_dicts(turn_context.products)
        sql_phases = build_hybrid_sql_phases(
            query=query,
            turn_context=turn_context,
            query_embedding=query_embedding,
            embedding_ms=embedding_ms,
            oracle_ms=oracle_ms,
            embedding_cache_hit=embedding_cache_hit,
        )

        if turn_context.off_menu_terms:
            off_menu_term = turn_context.off_menu_terms[0].title()
            answer = _render_off_menu_alternative(off_menu_term, products)
            grounded_ms = (time.perf_counter() - started) * 1000
            total_ms = embedding_ms + oracle_ms + grounded_ms
            metrics = build_search_metrics(
                query=query,
                turn_context=turn_context,
                total_ms=total_ms,
                embedding_ms=embedding_ms,
                oracle_ms=oracle_ms,
                grounded_answer_mode="off_menu_guard",
                grounded_answer_ms=grounded_ms,
            )
            return GroundedTurnResult(
                answer=answer,
                intent_detected="PRODUCT_RAG",
                search_metrics=metrics,
                sql_phases=sql_phases,
                embedding_cache_hit=embedding_cache_hit,
                location_context=safe_location_context(location_context),
                last_products=[str(p["name"]) for p in products] if products else None,
            )

        answer, mode, grounded_ms = await _compose_grounded_answer(
            query=query, products=products, vertex_ai_service=self.vertex_ai_service, persona=persona
        )
        total_ms = embedding_ms + oracle_ms + grounded_ms
        metrics = build_search_metrics(
            query=query,
            turn_context=turn_context,
            total_ms=total_ms,
            embedding_ms=embedding_ms,
            oracle_ms=oracle_ms,
            grounded_answer_mode=mode,
            grounded_answer_ms=grounded_ms,
        )
        return GroundedTurnResult(
            answer=answer,
            intent_detected="PRODUCT_RAG",
            search_metrics=metrics,
            sql_phases=sql_phases,
            embedding_cache_hit=embedding_cache_hit,
            location_context=safe_location_context(location_context),
            last_products=[str(p["name"]) for p in products] if products else None,
        )

    async def handle_store_location(
        self,
        query: str,
        turn_context: HybridTurnContext,
        *,
        location_context: dict[str, Any] | None = None,
        embedding_ms: float = 0.0,
        oracle_ms: float = 0.0,
        embedding_cache_hit: bool = False,
        query_embedding: list[float] | None = None,
    ) -> GroundedTurnResult:
        """Resolve store locations from coordinates, location filters, or RRF store candidates."""
        started = time.perf_counter()
        sql_phases = build_hybrid_sql_phases(
            query=query,
            turn_context=turn_context,
            query_embedding=query_embedding,
            embedding_ms=embedding_ms,
            oracle_ms=oracle_ms,
            embedding_cache_hit=embedding_cache_hit,
        )
        coordinates = request_coordinates(location_context)
        if coordinates is not None:
            lookup_started = time.perf_counter()
            nearest = await self.store_service.find_nearest_stores(coordinates[0], coordinates[1], limit=5)
            lookup_ms = (time.perf_counter() - lookup_started) * 1000
            stores = _coerce_dict_rows(sanitize_for_json(nearest))
            sql_phases.append(
                build_sql_phase(
                    label="Nearest store lookup",
                    sql_key="list-stores",
                    binds={"origin": "<REQUEST_COORDINATES>", "limit": 5},
                    row_count=len(stores),
                    runtime_ms=lookup_ms,
                )
            )
        else:
            filters = extract_location_filters(query, location_context)
            lookup_started = time.perf_counter()
            matched_stores = await self.store_service.find_stores_by_location(
                city=filters["city"], state=filters["state"], zip_code=filters["zip_code"]
            )
            lookup_ms = (time.perf_counter() - lookup_started) * 1000
            stores = _coerce_dict_rows(sanitize_for_json(matched_stores))
            if not stores and turn_context.stores:
                stores = [
                    {
                        "id": candidate.id,
                        "name": candidate.name,
                        "city": candidate.city or "",
                        "state": candidate.state or "",
                        "address": candidate.address or "",
                    }
                    for candidate in turn_context.stores
                ]
            sql_phases.append(
                build_sql_phase(
                    label="Store location lookup",
                    sql_key="find-stores-by-location",
                    binds={"city": filters["city"], "state": filters["state"], "zip_code": filters["zip_code"]},
                    row_count=len(stores),
                    runtime_ms=lookup_ms,
                )
            )

        answer = _format_store_location_answer(stores)
        total_ms = embedding_ms + oracle_ms + (time.perf_counter() - started) * 1000
        metrics = build_search_metrics(
            query=query,
            turn_context=turn_context,
            total_ms=total_ms,
            embedding_ms=embedding_ms,
            oracle_ms=oracle_ms,
            results_count=len(stores),
        )
        return GroundedTurnResult(
            answer=answer,
            intent_detected="STORE_LOCATION",
            search_metrics=metrics,
            sql_phases=sql_phases,
            embedding_cache_hit=embedding_cache_hit,
            store_results=stores,
            map_actions=build_map_actions(stores),
            location_context=safe_location_context(location_context),
        )

    async def handle_product_availability(
        self,
        query: str,
        turn_context: HybridTurnContext,
        *,
        location_context: dict[str, Any] | None = None,
        last_products: list[str] | None = None,
        embedding_ms: float = 0.0,
        oracle_ms: float = 0.0,
        embedding_cache_hit: bool = False,
        query_embedding: list[float] | None = None,
    ) -> GroundedTurnResult:
        """Resolve store-level inventory availability for a product and optional target store."""
        started = time.perf_counter()
        sql_phases = build_hybrid_sql_phases(
            query=query,
            turn_context=turn_context,
            query_embedding=query_embedding,
            embedding_ms=embedding_ms,
            oracle_ms=oracle_ms,
            embedding_cache_hit=embedding_cache_hit,
        )
        coordinates = request_coordinates(location_context)
        product_query = _resolve_product_query(query, turn_context, last_products)
        target_store = await self.store_service.resolve_store(
            location_hint=_resolve_location_hint(query, location_context), coordinates=coordinates
        )
        inventory, availability_phase = await self._fetch_availability_inventory(
            product_query=product_query, turn_context=turn_context, coordinates=coordinates
        )
        sql_phases.append(availability_phase)

        target_row, alternatives = _partition_availability_rows(
            inventory, target_store.id if target_store is not None else None
        )
        answer = _format_availability_answer(
            target=target_row,
            alternatives=alternatives,
            target_store_name=target_store.name if target_store is not None else None,
        )
        total_ms = embedding_ms + oracle_ms + (time.perf_counter() - started) * 1000
        metrics = build_search_metrics(
            query=query,
            turn_context=turn_context,
            total_ms=total_ms,
            embedding_ms=embedding_ms,
            oracle_ms=oracle_ms,
            results_count=len(inventory),
            product_query=product_query,
        )
        return GroundedTurnResult(
            answer=answer,
            intent_detected="PRODUCT_AVAILABILITY",
            search_metrics=metrics,
            sql_phases=sql_phases,
            embedding_cache_hit=embedding_cache_hit,
            inventory_results=inventory,
            map_actions=build_map_actions(inventory),
            location_context=safe_location_context(location_context),
        )

    async def handle_order_status(
        self,
        query: str,
        turn_context: HybridTurnContext,
        *,
        location_context: dict[str, Any] | None = None,
        embedding_ms: float = 0.0,
        oracle_ms: float = 0.0,
        embedding_cache_hit: bool = False,
        query_embedding: list[float] | None = None,
    ) -> GroundedTurnResult:
        """Return the deterministic unsupported order-tracking message."""
        sql_phases = build_hybrid_sql_phases(
            query=query,
            turn_context=turn_context,
            query_embedding=query_embedding,
            embedding_ms=embedding_ms,
            oracle_ms=oracle_ms,
            embedding_cache_hit=embedding_cache_hit,
        )
        total_ms = embedding_ms + oracle_ms
        metrics = build_search_metrics(
            query=query,
            turn_context=turn_context,
            total_ms=total_ms,
            embedding_ms=embedding_ms,
            oracle_ms=oracle_ms,
            results_count=0,
        )
        return GroundedTurnResult(
            answer=_ORDER_STATUS_ANSWER,
            intent_detected="ORDER_STATUS",
            search_metrics=metrics,
            sql_phases=sql_phases,
            embedding_cache_hit=embedding_cache_hit,
            location_context=safe_location_context(location_context),
        )

    async def _fetch_availability_inventory(
        self, *, product_query: str, turn_context: HybridTurnContext, coordinates: tuple[float, float] | None
    ) -> tuple[list[dict[str, Any]], SQLPhase]:
        lookup_started = time.perf_counter()
        lat, lon = coordinates if coordinates is not None else (None, None)
        if turn_context.products:
            top_product = turn_context.products[0]
            availability_rows = await self.store_service.find_stores_with_product(
                top_product.id, latitude=lat, longitude=lon
            )
            sql_key = "find-stores-with-product-inventory"
            binds: dict[str, Any] = {"product_id": top_product.id}
        else:
            availability_rows = await self.store_service.find_product_availability(
                product_query, coordinates=coordinates
            )
            sql_key = "find-product-availability-by-query"
            binds = {"product_query": product_query}

        if coordinates is not None:
            binds["origin"] = "<REQUEST_COORDINATES>"
        lookup_ms = (time.perf_counter() - lookup_started) * 1000
        inventory = _coerce_dict_rows(sanitize_for_json(availability_rows))
        phase = build_sql_phase(
            label="Product availability lookup",
            sql_key=sql_key,
            binds=binds,
            row_count=len(inventory),
            runtime_ms=lookup_ms,
        )
        return inventory, phase


def _resolve_product_query(query: str, turn_context: HybridTurnContext, last_products: list[str] | None) -> str:
    extracted = extract_product_query(query)
    if extracted:
        return extracted
    if turn_context.products:
        return turn_context.products[0].name
    if last_products:
        return last_products[0]
    return query


def _resolve_location_hint(query: str, location_context: dict[str, Any] | None) -> str:
    store_name = (location_context or {}).get("store_name") if location_context else None
    if store_name:
        return str(store_name)
    filters = extract_location_filters(query, location_context)
    return " ".join(str(filters[k]) for k in ("city", "state", "zip_code") if filters[k]) or query


def _partition_availability_rows(
    inventory: list[dict[str, Any]], target_store_id: int | None
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
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


def _candidates_to_dicts(
    candidates: list[HybridProductCandidate] | tuple[HybridProductCandidate, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "id": candidate.id,
            "name": candidate.name,
            "category": candidate.category,
            "price": candidate.price,
            "description": candidate.description,
            "similarity_score": candidate.vector_similarity,
            "rrf_score": candidate.rrf_score,
        }
        for candidate in candidates
    ]


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


def _format_price(value: Any) -> str:
    if not isinstance(value, int | float):
        return ""
    return f" (${value:.2f})"


def _render_selected_product(product: dict[str, Any]) -> str:
    name = str(product["name"])
    return f"{name}{_format_price(product.get('price'))}"


def _render_off_menu_alternative(off_menu_term: str, products: list[dict[str, Any]]) -> str:
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


def _grounded_product_answer(query: str, products: list[dict[str, Any]]) -> str:
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


def _candidate_id(product: dict[str, Any]) -> str:
    for key in ("id", "product_id", "sku", "name"):
        value = product.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return str(product["name"]).strip()


def _candidate_block(products: list[dict[str, Any]]) -> str:
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


def _render_grounded_selection(query: str, payload: dict[str, Any], selected: list[dict[str, Any]]) -> str | None:
    mode = str(payload.get("mode") or "").strip()
    explanation = str(payload.get("explanation") or "").strip()
    if mode == "recommend":
        base_answer = _grounded_product_answer(query, selected)
        if explanation:
            return f"{explanation} {base_answer}"
        return base_answer
    if mode == "off_menu_alternative":
        off_menu_term = str(payload.get("off_menu_term") or "that item")
        answer = _render_off_menu_alternative(off_menu_term, selected)
        if explanation:
            return f"{explanation} {answer}"
        return answer
    return None


def _is_credential_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    if isinstance(exc, genai_errors.ClientError):
        return any(
            marker in text
            for marker in (
                "api key",
                "credentials",
                "permission_denied",
                "service_disabled",
                "forbidden",
                "unauthorized",
            )
        )
    return "api key" in text or "credentials" in text


async def _compose_grounded_answer(
    *, query: str, products: list[dict[str, Any]], vertex_ai_service: VertexAIService | None, persona: str = "barista"
) -> tuple[str, str, float]:
    started = time.perf_counter()
    if not products or vertex_ai_service is None:
        return _grounded_product_answer(query, products), "template", (time.perf_counter() - started) * 1000

    contents = f"Customer request: {query}\n\nCandidate products (select only these ids):\n{_candidate_block(products)}"
    persona_config = PersonaManager.PERSONAS.get(persona, PersonaManager.PERSONAS["barista"])
    instruction = _GROUNDED_ANSWER_INSTRUCTION_TEMPLATE.format(persona_guidelines=persona_config.system_prompt_addon)
    settings = get_settings()
    try:
        async with asyncio.timeout(settings.chat.grounded_answer_timeout_seconds):
            response = await vertex_ai_service.generate_structured_content(
                model=settings.ai.chat_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=_GROUNDED_ANSWER_TEMPERATURE,
                    system_instruction=instruction,
                    response_mime_type="application/json",
                    response_schema=_GROUNDED_ANSWER_SCHEMA,
                ),
            )
    except TimeoutError:
        await logger.awarning("Grounded answer generation timed out")
        return _grounded_product_answer(query, products), "timeout", (time.perf_counter() - started) * 1000
    except Exception as exc:
        if _is_credential_error(exc):
            raise AIServiceUnconfigured(_UNCONFIGURED_MESSAGE) from exc
        await logger.awarning("Grounded answer generation failed", error_type=type(exc).__name__)
        return _grounded_product_answer(query, products), "error", (time.perf_counter() - started) * 1000

    payload = _response_payload(response)
    selected = _selected_products(payload, products) if payload is not None else None
    answer = (
        _render_grounded_selection(query, payload, selected) if payload is not None and selected is not None else None
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if answer is None:
        await logger.awarning("Grounded answer rejected by guard")
        return _grounded_product_answer(query, products), "rejected", elapsed_ms
    return answer, "structured", elapsed_ms


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
    found_clause = f". I found {len(available_alternatives)} stores with matching availability."
    return base_sentence + found_clause


__all__ = ("GroundedRouteService", "GroundedTurnResult")

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Deterministic grounded route orchestration for Cymbal Coffee chat turns."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

import msgspec
import structlog
from google.genai import types

from app.domain.chat.services._composers import (
    ORDER_STATUS_ANSWER,
    build_candidate_block,
    compose_availability_answer,
    compose_grounded_selection,
    compose_off_menu_alternative,
    compose_product_rag_answer,
    compose_store_location_answer,
    partition_availability_rows,
    select_grounded_products,
)
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
from app.lib.exceptions import AIServiceUnconfigured, is_credential_error, is_expected_service_unavailable
from app.lib.schema import FrozenBaseStruct
from app.lib.settings import Settings
from app.utils.serialization import decode_json, sanitize_for_json

if TYPE_CHECKING:
    from app.domain.chat.schemas import HybridProductCandidate, HybridRouteLabel, HybridTurnContext
    from app.domain.products.services import ProductService, StoreService, VertexAIService

__all__ = ("GroundedRouteService", "GroundedTurnResult")

logger = structlog.get_logger()

_UNCONFIGURED_MESSAGE = "AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file."
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


class GroundedTurnResult(FrozenBaseStruct, frozen=True, gc=False, kw_only=True):
    """Completed deterministic turn payload ready for caching and SSE emission."""

    answer: str
    intent_detected: HybridRouteLabel
    search_metrics: SearchMetrics
    sql_phases: list[SQLPhase]
    embedding_cache_hit: bool = False
    store_results: list[dict[str, Any]] = msgspec.field(default_factory=list)
    inventory_results: list[dict[str, Any]] = msgspec.field(default_factory=list)
    map_actions: list[dict[str, str]] = msgspec.field(default_factory=list)
    location_context: dict[str, Any] = msgspec.field(default_factory=dict)
    last_products: list[str] | None = None


class GroundedRouteService:
    """Orchestrates deterministic responses for PRODUCT_RAG, STORE_LOCATION, PRODUCT_AVAILABILITY, and ORDER_STATUS."""

    __slots__ = ("product_service", "store_service", "vertex_ai_service")

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
            answer = compose_off_menu_alternative(off_menu_term, products)
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

        answer = compose_store_location_answer(stores)
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

        target_row, alternatives = partition_availability_rows(
            inventory, target_store.id if target_store is not None else None
        )
        answer = compose_availability_answer(
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
            answer=ORDER_STATUS_ANSWER,
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
        query_folded = product_query.casefold()
        matched_candidate = next(
            (
                candidate
                for candidate in turn_context.products
                if candidate.name.casefold() == query_folded or query_folded in candidate.name.casefold()
            ),
            None,
        )
        if matched_candidate is not None:
            availability_rows = await self.store_service.find_stores_with_product(
                matched_candidate.id, latitude=lat, longitude=lon
            )
            sql_key = "find-stores-with-product-inventory"
            binds: dict[str, Any] = {"product_id": matched_candidate.id}
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
    query_folded = query.casefold()
    for candidate in turn_context.products:
        if candidate.name.casefold() in query_folded:
            return candidate.name
    extracted = extract_product_query(query)
    if extracted:
        return extracted
    if last_products:
        return last_products[0]
    if turn_context.products:
        return turn_context.products[0].name
    return query


def _resolve_location_hint(query: str, location_context: dict[str, Any] | None) -> str:
    store_name = (location_context or {}).get("store_name") if location_context else None
    if store_name:
        return str(store_name)
    filters = extract_location_filters(query, location_context)
    return " ".join(str(filters[k]) for k in ("city", "state", "zip_code") if filters[k]) or query


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


def _response_payload(response: Any) -> dict[str, Any] | None:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, dict):
        return parsed
    text = getattr(response, "text", None)
    if not isinstance(text, str | bytes) or not text:
        return None
    try:
        payload = decode_json(text)
    except msgspec.DecodeError:
        return None
    return payload if isinstance(payload, dict) else None


async def _compose_grounded_answer(
    *, query: str, products: list[dict[str, Any]], vertex_ai_service: VertexAIService | None, persona: str = "barista"
) -> tuple[str, str, float]:
    started = time.perf_counter()
    if not products or vertex_ai_service is None:
        return compose_product_rag_answer(query, products), "template", (time.perf_counter() - started) * 1000

    contents = (
        f"Customer request: {query}\n\nCandidate products (select only these ids):\n{build_candidate_block(products)}"
    )
    persona_config = PersonaManager.PERSONAS.get(persona, PersonaManager.PERSONAS["barista"])
    instruction = _GROUNDED_ANSWER_INSTRUCTION_TEMPLATE.format(persona_guidelines=persona_config.system_prompt_addon)
    settings = Settings.from_env()
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
        return compose_product_rag_answer(query, products), "timeout", (time.perf_counter() - started) * 1000
    except Exception as exc:
        if is_credential_error(exc) or is_expected_service_unavailable(exc):
            raise AIServiceUnconfigured(_UNCONFIGURED_MESSAGE) from exc
        await logger.awarning("Grounded answer generation failed", error_type=type(exc).__name__)
        return compose_product_rag_answer(query, products), "error", (time.perf_counter() - started) * 1000

    payload = _response_payload(response)
    selected = (
        select_grounded_products(payload, products, allowed_modes=_GROUNDED_SELECTION_MODES)
        if payload is not None
        else None
    )
    answer = (
        compose_grounded_selection(query, payload, selected) if payload is not None and selected is not None else None
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if answer is None:
        await logger.awarning("Grounded answer rejected by guard")
        return compose_product_rag_answer(query, products), "rejected", elapsed_ms
    return answer, "structured", elapsed_ms

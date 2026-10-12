# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Grounded agent tools bound to request-scoped services via CallContext."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.domain.ai.runtime._context import CallContext
from app.domain.ai.runtime._tools import Tool, declare
from app.domain.chat.services._router import build_oracle_text_query
from app.domain.chat.services._telemetry import (
    build_map_actions,
    build_sql_phase,
    request_coordinates,
    summarize_vector,
)
from app.utils.serialization import sanitize_for_json

if TYPE_CHECKING:
    from app.domain.products.services import ProductService, StoreService, VertexAIService
    from app.domain.system.services import MetricsService

__all__ = (
    "CoffeeToolServices",
    "build_coffee_tools",
    "check_order_status",
    "check_product_availability",
    "find_nearby_stores",
    "get_product_details",
    "search_products",
)

_ORDER_UNSUPPORTED_MESSAGE = (
    "This demo does not include order tracking yet. I can help with menu recommendations, "
    "store locations, and product availability."
)


@dataclass(slots=True)
class CoffeeToolServices:
    """Request-scoped domain services made available to agent tools via CallContext.services."""

    product_service: ProductService | None = None
    store_service: StoreService | None = None
    vertex_ai_service: VertexAIService | None = None
    metrics_service: MetricsService | None = None


async def search_products(ctx: CallContext, query: str, limit: int = 5) -> dict[str, Any]:
    """Search the Cymbal Coffee product catalog using Oracle 26ai Hybrid RRF search.

    Args:
        ctx: Active agent call context.
        query: Natural-language search query for coffee roasts, flavors, or origins.
        limit: Maximum number of products to return.

    Returns:
        Dictionary containing matched products and result count.
    """
    bundle = _resolve_bundle(ctx)
    if bundle.product_service is None or bundle.vertex_ai_service is None:
        return {"products": [], "results_count": 0}

    bounded_limit = max(1, min(limit, 10))
    embed_started = time.perf_counter()
    embedding, cache_hit = await bundle.vertex_ai_service.get_text_embedding(
        query,
        embedding_purpose="query",
        return_cache_status=True,
    )
    embed_ms = (time.perf_counter() - embed_started) * 1000
    text_query = build_oracle_text_query(query)

    oracle_started = time.perf_counter()
    products = await bundle.product_service.search_hybrid(
        text_query=text_query,
        query_embedding=embedding,
        limit=bounded_limit,
    )
    oracle_ms = (time.perf_counter() - oracle_started) * 1000
    serialized = _coerce_list(sanitize_for_json(products))

    ctx.state["embedding_cache_hit"] = bool(cache_hit)
    sql_phases = ctx.state.setdefault("sql_phases", [])
    sql_phases.append(
        build_sql_phase(
            label="Oracle Hybrid RRF product search",
            sql_key="hybrid-search-products",
            binds={
                "has_text_query": 1 if text_query is not None else 0,
                "text_query": text_query or "{coffee}",
                "query_vector": summarize_vector(embedding),
                "limit": bounded_limit,
            },
            row_count=len(serialized),
            runtime_ms=oracle_ms,
        ).to_dict()
    )
    metrics = ctx.state.setdefault("search_metrics", {})
    metrics.update({
        "vector_query": query,
        "embedding_ms": round(embed_ms, 2),
        "oracle_ms": round(oracle_ms, 2),
        "results_count": len(serialized),
        "products_found": len(serialized),
    })
    return {"products": serialized, "results_count": len(serialized)}


async def get_product_details(ctx: CallContext, product_id_or_name: str) -> dict[str, Any]:
    """Retrieve complete details for a single Cymbal Coffee product by ID or name.

    Args:
        ctx: Active agent call context.
        product_id_or_name: Numeric product ID or exact product name.

    Returns:
        Dictionary with product fields or an error message if not found.
    """
    bundle = _resolve_bundle(ctx)
    if bundle.product_service is None:
        return {"error": "Product service unavailable"}

    cleaned = product_id_or_name.strip()
    try:
        product = await bundle.product_service.get_by_id(int(cleaned))
    except ValueError:
        product = await bundle.product_service.get_by_name(cleaned)

    if product is None:
        return {"error": f"Product '{cleaned}' not found"}
    serialized = sanitize_for_json(product)
    return serialized if isinstance(serialized, dict) else {"product": serialized}


async def find_nearby_stores(
    ctx: CallContext,
    city: str = "",
    state: str = "",
    zip_code: str = "",
    limit: int = 5,
) -> dict[str, Any]:
    """Find Cymbal Coffee store locations by browser coordinates or city/state/ZIP filters.

    Args:
        ctx: Active agent call context.
        city: Optional city filter.
        state: Optional two-letter state filter.
        zip_code: Optional 5-digit ZIP code filter.
        limit: Maximum number of stores to return.

    Returns:
        Dictionary containing matched store rows and Google Maps action URLs.
    """
    bundle = _resolve_bundle(ctx)
    if bundle.store_service is None:
        return {"stores": [], "map_actions": [], "results_count": 0}

    bounded_limit = max(1, min(limit, 10))
    location_context = ctx.state.get("location_context")
    coordinates = request_coordinates(location_context if isinstance(location_context, dict) else None)
    started = time.perf_counter()

    raw_stores: list[Any]
    if coordinates is not None:
        raw_stores = await bundle.store_service.find_nearest_stores(coordinates[0], coordinates[1], bounded_limit)
        sql_key = "list-stores"
        binds: dict[str, Any] = {"origin": "<REQUEST_COORDINATES>", "limit": bounded_limit}
    else:
        raw_stores = await bundle.store_service.find_stores_by_location(
            city=city.strip() or None,
            state=state.strip() or None,
            zip_code=zip_code.strip() or None,
        )
        sql_key = "find-stores-by-location"
        binds = {
            "city": city.strip() or None,
            "state": state.strip() or None,
            "zip_code": zip_code.strip() or None,
        }

    runtime_ms = (time.perf_counter() - started) * 1000
    stores = _coerce_list(sanitize_for_json(raw_stores))
    map_actions = build_map_actions(stores)
    ctx.state["store_results"] = stores
    ctx.state["map_actions"] = map_actions
    ctx.state.setdefault("sql_phases", []).append(
        build_sql_phase(
            label="Store location lookup",
            sql_key=sql_key,
            binds=binds,
            row_count=len(stores),
            runtime_ms=runtime_ms,
        ).to_dict()
    )
    return {"stores": stores, "map_actions": map_actions, "results_count": len(stores)}


async def check_product_availability(
    ctx: CallContext,
    product_query: str,
    location_hint: str = "",
) -> dict[str, Any]:
    """Check store-level inventory availability for a Cymbal Coffee product.

    Args:
        ctx: Active agent call context.
        product_query: Product name or roast phrase to check in store inventory.
        location_hint: Optional store name, neighborhood, city, or ZIP code.

    Returns:
        Dictionary containing store availability rows and Google Maps action URLs.
    """
    bundle = _resolve_bundle(ctx)
    if bundle.store_service is None:
        return {"availability": [], "map_actions": [], "results_count": 0}

    location_context = ctx.state.get("location_context")
    coordinates = request_coordinates(location_context if isinstance(location_context, dict) else None)
    started = time.perf_counter()
    raw_availability = await bundle.store_service.find_product_availability(
        product_query.strip(),
        location_hint=location_hint.strip() or None,
        coordinates=coordinates,
    )
    runtime_ms = (time.perf_counter() - started) * 1000
    availability = _coerce_list(sanitize_for_json(raw_availability))
    map_actions = build_map_actions(availability)
    binds: dict[str, Any] = {"product_query": product_query.strip()}
    if coordinates is not None:
        binds["origin"] = "<REQUEST_COORDINATES>"

    ctx.state["inventory_results"] = availability
    ctx.state["map_actions"] = map_actions
    ctx.state.setdefault("sql_phases", []).append(
        build_sql_phase(
            label="Product availability lookup",
            sql_key="find-product-availability-by-query",
            binds=binds,
            row_count=len(availability),
            runtime_ms=runtime_ms,
        ).to_dict()
    )
    return {"availability": availability, "map_actions": map_actions, "results_count": len(availability)}


def check_order_status(ctx: CallContext, order_id: str = "") -> dict[str, Any]:
    """Return the explicit order-tracking capability status for the Cymbal Coffee demo.

    Args:
        ctx: Active agent call context.
        order_id: Optional customer order identifier.

    Returns:
        Dictionary stating that order tracking is not yet enabled in this demo.
    """
    del ctx
    return {
        "supported": False,
        "order_id": order_id.strip(),
        "message": _ORDER_UNSUPPORTED_MESSAGE,
    }


def build_coffee_tools() -> tuple[Tool, ...]:
    """Build and return the 5 grounded Cymbal Coffee agent tools."""
    return (
        declare(search_products),
        declare(get_product_details),
        declare(find_nearby_stores),
        declare(check_product_availability),
        declare(check_order_status),
    )


def _resolve_bundle(ctx: CallContext) -> CoffeeToolServices:
    if isinstance(ctx.services, CoffeeToolServices):
        return ctx.services
    return CoffeeToolServices()


def _coerce_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]

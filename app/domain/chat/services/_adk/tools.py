"""ADK Tool Functions - Thin wrappers around AgentToolsService.

These functions provide the ADK tool interface while delegating
to the AgentToolsService for business logic.

Since ADK tool functions are called outside the HTTP request context,
we create request-scoped containers on-demand for each tool invocation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.domain.chat.services._adk.tool_service import AgentToolsService
from app.utils.serialization import from_json
from app.lib.di import request_container_var

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

async def search_products_by_vector(
    query: str,
    limit: int,
    similarity_threshold: float,
) -> dict[str, Any]:
    """Search for coffee products using vector similarity with fresh session."""
    # Apply defaults within function to avoid ADK schema issues
    limit = limit or 5
    similarity_threshold = similarity_threshold or 0.7

    # Create request-scoped container for this tool invocation
    request_container = request_container_var.get()
    if not request_container:
        raise RuntimeError("No active request container found in context.")
    tools_service = await request_container.get(AgentToolsService)
    return await tools_service.search_products_by_vector(query, limit, similarity_threshold)

async def get_product_details(product_id: str) -> dict[str, Any]:
    """Get detailed information about a specific product by ID or name with fresh session."""
    request_container = request_container_var.get()
    if not request_container:
        raise RuntimeError("No active request container found in context.")
    tools_service = await request_container.get(AgentToolsService)
    return await tools_service.get_product_details(product_id)


async def classify_intent(query: str) -> dict[str, Any]:
    """Classify user intent using vector-based classification with fresh session."""
    request_container = request_container_var.get()
    if not request_container:
        raise RuntimeError("No active request container found in context.")
    tools_service = await request_container.get(AgentToolsService)
    return await tools_service.classify_intent(query)


async def record_search_metric(
    session_id: str,
    query_text: str,
    intent: str,
    response_time_ms: float,
    vector_search_time_ms: int = 0,
    vector_results_json: str = "[]",
) -> dict[str, Any]:
    """Record metrics for search performance with fresh session."""
    request_container = request_container_var.get()
    if not request_container:
        raise RuntimeError("No active request container found in context.")
    tools_service = await request_container.get(AgentToolsService)

    from app.lib.di import QueryContext

    query_context = await request_container.get(QueryContext | None)
    query_id = query_context.query_id if query_context else None

    vector_results = from_json(vector_results_json) if vector_results_json else []

    return await tools_service.record_search_metric(
        session_id=session_id,
        query_text=query_text,
        intent=intent,
        vector_results=vector_results,
        total_response_time_ms=int(response_time_ms),
        vector_search_time_ms=vector_search_time_ms,
        query_id=query_id,
    )


async def get_store_locations() -> list[dict[str, Any]]:
    """Get all store locations and information with fresh session."""
    request_container = request_container_var.get()
    if not request_container:
        raise RuntimeError("No active request container found in context.")
    tools_service = await request_container.get(AgentToolsService)
    return await tools_service.get_all_store_locations()


async def find_stores_by_location(city: str = "", state: str = "") -> list[dict[str, Any]]:
    """Find stores in a specific location with fresh session."""
    request_container = request_container_var.get()
    if not request_container:
        raise RuntimeError("No active request container found in context.")
    tools_service = await request_container.get(AgentToolsService)
    # Convert empty strings to None for the service layer
    city_filter = city or None
    state_filter = state or None
    return await tools_service.find_stores_by_location(city_filter, state_filter)


async def get_store_hours(store_id: int) -> dict[str, Any]:
    """Get store hours for a specific store with fresh session."""
    request_container = request_container_var.get()
    if not request_container:
        raise RuntimeError("No active request container found in context.")
    tools_service = await request_container.get(AgentToolsService)
    return await tools_service.get_store_hours(store_id)


# List of all available tool functions
ALL_TOOLS: Sequence[Callable[..., Any]] = [
    search_products_by_vector,
    get_product_details,
    classify_intent,
    record_search_metric,
    get_store_locations,
    find_stores_by_location,
    get_store_hours,
]

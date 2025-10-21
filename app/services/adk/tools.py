"""ADK Tool Functions - Thin wrappers around AgentToolsService.

These functions provide the ADK tool interface while delegating
to the AgentToolsService for business logic.

Since ADK tool functions are called outside the HTTP request context,
we create request-scoped containers on-demand for each tool invocation.
"""

from __future__ import annotations

from typing import Any, cast

from dishka import AsyncContainer

from app.services.adk.tool_service import AgentToolsService
from app.utils.serialization import from_json

# Global container reference set by the application
_app_container: AsyncContainer | None = None


def set_app_container(container: AsyncContainer) -> None:
    """Set the application container for ADK tools.

    This should be called during application startup to provide
    the container to tool functions.
    """
    global _app_container
    _app_container = container


def get_app_container() -> AsyncContainer:
    """Get the application container.

    Raises:
        RuntimeError: If container hasn't been set
    """
    if _app_container is None:
        msg = "Application container not set. Call set_app_container() during app startup."
        raise RuntimeError(msg)
    return _app_container


async def search_products_by_vector(
    query: str,
    limit: int,
    similarity_threshold: float,
) -> list[dict[str, Any]]:
    """Search for coffee products using vector similarity with fresh session."""
    # Apply defaults within function to avoid ADK schema issues
    limit = limit or 5
    similarity_threshold = similarity_threshold or 0.7

    # Create request-scoped container for this tool invocation
    container = get_app_container()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)
        result = await tools_service.search_products_by_vector(query, limit, similarity_threshold)
        return cast("list[dict[str, Any]]", result["products"])


async def get_product_details(product_id: str) -> dict[str, Any]:
    """Get detailed information about a specific product by ID or name with fresh session."""
    container = get_app_container()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)
        return await tools_service.get_product_details(product_id)


async def classify_intent(query: str) -> dict[str, Any]:
    """Classify user intent using vector-based classification with fresh session."""
    container = get_app_container()
    async with container() as request_container:
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
    """Record metrics for search performance with fresh session.

    Args:
        session_id: Session identifier
        query_text: The search query text
        intent: Detected intent
        response_time_ms: Total response time in milliseconds
        vector_search_time_ms: Time spent on vector search (default: 0)
        vector_results_json: JSON string of vector search results (default: "[]")

    Returns:
        Dictionary containing the recorded metrics
    """
    container = get_app_container()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)

        # Decode JSON string to list using SQLSpec's from_json utility
        vector_results = from_json(vector_results_json) if vector_results_json else []

        return await tools_service.record_search_metric(
            session_id=session_id,
            query_text=query_text,
            intent=intent,
            vector_results=vector_results,
            total_response_time_ms=int(response_time_ms),
            vector_search_time_ms=vector_search_time_ms,
        )


async def get_store_locations() -> list[dict[str, Any]]:
    """Get all store locations and information with fresh session."""
    container = get_app_container()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)
        return await tools_service.get_all_store_locations()


async def find_stores_by_location(city: str = "", state: str = "") -> list[dict[str, Any]]:
    """Find stores in a specific location with fresh session.

    Args:
        city: City name to search for stores (optional, use empty string for no filter)
        state: State abbreviation to search for stores (optional, use empty string for no filter)

    Returns:
        List of stores matching the location criteria
    """
    container = get_app_container()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)
        # Convert empty strings to None for the service layer
        city_filter = city if city else None
        state_filter = state if state else None
        return await tools_service.find_stores_by_location(city_filter, state_filter)


async def get_store_hours(store_id: int) -> dict[str, Any]:
    """Get store hours for a specific store with fresh session."""
    container = get_app_container()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)
        return await tools_service.get_store_hours(store_id)


# List of all available tool functions
ALL_TOOLS = [
    search_products_by_vector,
    get_product_details,
    classify_intent,
    record_search_metric,
    get_store_locations,
    find_stores_by_location,
    get_store_hours,
]

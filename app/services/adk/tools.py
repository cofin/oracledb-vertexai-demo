"""ADK Tool Functions - Thin wrappers around AgentToolsService.

These functions provide the ADK tool interface while delegating
to the AgentToolsService for business logic.
"""

from __future__ import annotations

from typing import Any, cast

from app.config import db, db_manager, service_locator
from app.lib.context import clear_timing_context, set_timing_data
from app.services.adk.tool_service import AgentToolsService


def get_and_clear_timing_context() -> dict[str, Any]:
    """Get and clear the timing context data.

    Returns:
        The current timing context data
    """
    return clear_timing_context()


async def search_products_by_vector(
    query: str,
    limit: int,
    similarity_threshold: float,
) -> list[dict[str, Any]]:
    """Search for coffee products using vector similarity with fresh session.

    Args:
        query: Customer's product query or description
        limit: Maximum number of products to return (1-20)
        similarity_threshold: Minimum similarity score 0.0-1.0

    Returns:
        List of matching products with details and similarity scores
    """
    # Apply defaults within function to avoid ADK schema issues
    limit = limit or 5
    similarity_threshold = similarity_threshold or 0.7
    async with db_manager.provide_session(db) as session:
        tools_service = service_locator.get(AgentToolsService, session)
        result = await tools_service.search_products_by_vector(query, limit, similarity_threshold)

        # Store timing data for orchestrator access
        set_timing_data(
            "vector_search",
            {
                "total_ms": result["timing"]["total_ms"],
                "embedding_ms": result["timing"]["embedding_ms"],
                "search_ms": result["timing"]["search_ms"],
                "embedding_cache_hit": result["embedding_cache_hit"],
                "vector_search_cache_hit": result["vector_search_cache_hit"],
                "sql_query": result["sql_query"],
                "params": result["params"],
                "results_count": result["results_count"],
            },
        )

        # Return just the products list for ADK compatibility
        return cast("list[dict[str, Any]]", result["products"])


async def get_product_details(product_id: str) -> dict[str, Any]:
    """Get detailed information about a specific product by ID or name with fresh session.

    Args:
        product_id: Product UUID or name to look up

    Returns:
        Product details or error message
    """
    async with db_manager.provide_session(db) as session:
        tools_service = service_locator.get(AgentToolsService, session)
        return await tools_service.get_product_details(product_id)


async def classify_intent(query: str) -> dict[str, Any]:
    """Classify user intent using vector-based classification with fresh session.

    Args:
        query: User's message to classify

    Returns:
        Intent classification results
    """
    async with db_manager.provide_session(db) as session:
        tools_service = service_locator.get(AgentToolsService, session)
        result = await tools_service.classify_intent(query)

        # Store timing data for orchestrator access
        set_timing_data("intent_classification", {"timing_ms": result["timing_ms"], "sql_query": result["sql_query"]})

        return result


async def record_search_metric(
    session_id: str,
    query_text: str,
    intent: str,
    response_time_ms: float,
    vector_search_time_ms: int,
    vector_results: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Record metrics for search performance with fresh session.

    Args:
        session_id: Session identifier
        query_text: The search query
        intent: Detected intent
        response_time_ms: Total response time
        vector_search_time_ms: Time spent on vector search
        vector_results: Vector search results

    Returns:
        Status of metric recording
    """
    async with db_manager.provide_session(db) as session:
        tools_service = service_locator.get(AgentToolsService, session)
        # Apply defaults within function to avoid ADK schema issues
        vector_search_time_ms = vector_search_time_ms or 0
        vector_results = vector_results or []

        return await tools_service.record_search_metric(
            session_id=session_id,
            query_text=query_text,
            intent=intent,
            vector_results=vector_results,
            total_response_time_ms=int(response_time_ms),
            vector_search_time_ms=vector_search_time_ms,
        )


async def get_store_locations() -> list[dict[str, Any]]:
    """Get all store locations and information with fresh session.

    Returns:
        List of all coffee shop locations with details
    """
    async with db_manager.provide_session(db) as session:
        tools_service = service_locator.get(AgentToolsService, session)
        return await tools_service.get_all_store_locations()


async def find_stores_by_location(city: str | None, state: str | None) -> list[dict[str, Any]]:
    """Find stores in a specific location with fresh session.

    Args:
        city: City name to search for (optional)
        state: State to search for (optional)

    Returns:
        List of stores matching the location criteria
    """
    async with db_manager.provide_session(db) as session:
        tools_service = service_locator.get(AgentToolsService, session)
        return await tools_service.find_stores_by_location(city, state)


async def get_store_hours(store_id: int) -> dict[str, Any]:
    """Get store hours for a specific store with fresh session.

    Args:
        store_id: Store ID

    Returns:
        Store hours information
    """
    async with db_manager.provide_session(db) as session:
        tools_service = service_locator.get(AgentToolsService, session)
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

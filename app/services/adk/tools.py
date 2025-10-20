"""ADK Tool Functions - Thin wrappers around AgentToolsService.

These functions provide the ADK tool interface while delegating
to the AgentToolsService for business logic.
"""

from __future__ import annotations

from typing import Any, cast

from app.config import db, db_manager
from app.services.adk.tool_service import AgentToolsService
from app.utils.serialization import from_json


async def search_products_by_vector(
    query: str,
    limit: int,
    similarity_threshold: float,
) -> list[dict[str, Any]]:
    """Search for coffee products using vector similarity with fresh session."""
    # Apply defaults within function to avoid ADK schema issues
    limit = limit or 5
    similarity_threshold = similarity_threshold or 0.7
    async with db_manager.provide_session(db) as session:
        from app.config import service_locator
        tools_service = service_locator.get(AgentToolsService, session)
        result = await tools_service.search_products_by_vector(query, limit, similarity_threshold)
        return cast("list[dict[str, Any]]", result["products"])


async def get_product_details(product_id: str) -> dict[str, Any]:
    """Get detailed information about a specific product by ID or name with fresh session."""
    async with db_manager.provide_session(db) as session:
        from app.config import service_locator
        tools_service = service_locator.get(AgentToolsService, session)
        return await tools_service.get_product_details(product_id)


async def classify_intent(query: str) -> dict[str, Any]:
    """Classify user intent using vector-based classification with fresh session."""
    async with db_manager.provide_session(db) as session:
        from app.config import service_locator
        tools_service = service_locator.get(AgentToolsService, session)
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
    async with db_manager.provide_session(db) as session:
        from app.config import service_locator

        tools_service = service_locator.get(AgentToolsService, session)

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
    async with db_manager.provide_session(db) as session:
        from app.config import service_locator
        tools_service = service_locator.get(AgentToolsService, session)
        return await tools_service.get_all_store_locations()


async def find_stores_by_location(city: str = "", state: str = "") -> list[dict[str, Any]]:
    """Find stores in a specific location with fresh session.

    Args:
        city: City name to search for stores (optional, use empty string for no filter)
        state: State abbreviation to search for stores (optional, use empty string for no filter)

    Returns:
        List of stores matching the location criteria
    """
    async with db_manager.provide_session(db) as session:
        from app.config import service_locator
        tools_service = service_locator.get(AgentToolsService, session)
        # Convert empty strings to None for the service layer
        city_filter = city if city else None
        state_filter = state if state else None
        return await tools_service.find_stores_by_location(city_filter, state_filter)


async def get_store_hours(store_id: int) -> dict[str, Any]:
    """Get store hours for a specific store with fresh session."""
    async with db_manager.provide_session(db) as session:
        from app.config import service_locator
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

"""ADK Agent Runner for the modern Coffee Assistant System.

This module provides the main runner class that manages the ADK agent system
using the proper ADK Runner pattern with our custom session service.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from google.adk import Runner
from google.genai import types
from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

from app.config import db
from app.services.adk.agent import CoffeeAssistantAgent
from app.services.adk.monkey_patches import apply_genai_client_patch

# Apply monkey patches for ADK library issues
apply_genai_client_patch()

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.sessions import Session

    from app.services.cache import CacheService

logger = structlog.get_logger()


class ADKRunner:
    """Main runner for the ADK-based coffee assistant system with response caching."""

    def __init__(self) -> None:
        """Initialize the ADK runner with SQLSpec session service."""
        store = OracleAsyncADKStore(config=db)
        self.session_service = SQLSpecSessionService(store)
        self.runner = Runner(
            agent=CoffeeAssistantAgent,
            app_name="coffee-assistant",
            session_service=self.session_service,
        )
        logger.debug("ADKRunner initialized with SQLSpec session service")

    async def process_request(
        self,
        query: str,
        user_id: str = "default",
        session_id: str | None = None,
        cache_service: CacheService | None = None,
    ) -> dict[str, Any]:
        """Process user request through the ADK agent system with detailed metrics tracking."""
        start_time = time.time()
        logger.debug("Processing request via ADKRunner...", query=query)

        session = await self._ensure_session(user_id, session_id)
        content = types.Content(role="user", parts=[types.Part(text=query)])

        agent_start = time.time()
        events = self.runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        )

        event_data = await self._process_events(events)
        agent_processing_ms = round((time.time() - agent_start) * 1000, 2)

        total_time_ms = round((time.time() - start_time) * 1000, 2)

        # Build response with all metadata like main branch RecommendationService
        return {
            "answer": event_data["final_response_text"],
            "session_id": session.id,
            "response_time_ms": total_time_ms,
            "agent_processing_ms": agent_processing_ms,
            "intent_details": event_data.get("intent_details", {}),
            "search_details": event_data.get("search_details", {}),
            "products_found": event_data.get("products_found", []),
            "embedding_cache_hit": event_data.get("embedding_cache_hit", False),
            "intent_detected": event_data.get("intent_details", {}).get("intent", "GENERAL_CONVERSATION"),
            "from_cache": False,  # TODO: Integrate response cache
        }

    async def _ensure_session(self, user_id: str, session_id: str | None) -> Session:
        """Ensure session exists using get-or-create pattern."""
        if session_id:
            existing = await self.session_service.get_session(
                app_name="coffee-assistant",
                user_id=user_id,
                session_id=session_id,
            )
            if existing:
                return existing

        return await self.session_service.create_session(
            app_name="coffee-assistant",
            user_id=user_id,
            session_id=session_id,
            state={},
        )

    async def _process_events(self, events: AsyncGenerator) -> dict[str, Any]:
        """Process ADK events to extract response and metrics.

        Collects text from all events and extracts metrics from function responses,
        similar to postgres orchestrator's _process_events method.

        Returns:
            Dictionary with final_response_text, intent_details, search_details,
            products_found, and embedding_cache_hit.
        """
        all_text_responses = []
        final_response_text = ""
        event_count = 0
        intent_details: dict[str, Any] = {}
        search_details: dict[str, Any] = {}
        products_found: list[Any] = []
        embedding_cache_hit = False

        async for event in events:
            event_count += 1

            # Extract text from this event
            text_parts = self._extract_text_from_event(event)
            if text_parts:
                text_content = "".join(text_parts)
                # Filter out tool-calling internal messages
                if not self._should_filter_text(text_content):
                    all_text_responses.append(text_content)

            # Check for final response
            if event.is_final_response() and text_parts:
                final_response_text = "".join(text_parts)

            # Extract metrics from function responses
            function_responses = event.get_function_responses() if hasattr(event, "get_function_responses") else []
            if function_responses:
                for func_response in function_responses:
                    if func_response.name == "classify_intent":
                        intent_result = func_response.response or {}
                        intent_details = {
                            "intent": intent_result.get("intent"),
                            "confidence": intent_result.get("confidence"),
                            "exemplar_phrase": intent_result.get("exemplar_phrase"),
                            "timing_ms": intent_result.get("timing_ms"),
                            "sql_query": intent_result.get("sql_query"),
                        }
                        # Track first embedding cache hit (for intent classification)
                        if intent_result.get("embedding_cache_hit"):
                            embedding_cache_hit = True

                    elif func_response.name == "search_products_by_vector":
                        search_result = func_response.response or {}
                        products_found = search_result.get("products", [])
                        timing = search_result.get("timing", {})
                        search_details = {
                            "sql_query": search_result.get("sql_query"),
                            "params": search_result.get("params"),
                            "results_count": search_result.get("results_count", 0),
                            "embedding_ms": timing.get("embedding_ms", 0),
                            "search_ms": timing.get("search_ms", 0),
                            "total_ms": timing.get("total_ms", 0),
                        }

        # Use final response if available, otherwise use collected responses
        if not final_response_text and all_text_responses:
            final_response_text = " ".join(all_text_responses)

        # Fallback: If still no response, generate one based on intent and tool results
        # This matches the postgres orchestrator pattern for handling incomplete agent responses
        if not final_response_text:
            final_response_text = self._generate_fallback_response(intent_details, products_found)
            logger.info(
                "Generated fallback response",
                intent=intent_details.get("intent"),
                products_count=len(products_found),
            )

        return {
            "final_response_text": final_response_text,
            "intent_details": intent_details,
            "search_details": search_details,
            "products_found": products_found,
            "embedding_cache_hit": embedding_cache_hit,
        }

    def _extract_text_from_event(self, event: Any) -> list[str]:
        """Extract text parts from an event."""
        if not (event.content and event.content.parts):
            return []
        return [part.text for part in event.content.parts if hasattr(part, "text") and part.text]

    def _should_filter_text(self, text: str) -> bool:
        """Check if text should be filtered out (internal tool-calling messages)."""
        keywords = ["calling function", "function call", "tool call", "classify_intent", "search_products"]
        return any(keyword in text.lower() for keyword in keywords)

    def _generate_fallback_response(self, intent_details: dict[str, Any], products_found: list[Any]) -> str:
        """Generate fallback response when agent doesn't provide one.

        This matches the postgres orchestrator's fallback pattern.
        """
        intent = intent_details.get("intent", "GENERAL_CONVERSATION")

        if intent == "PRODUCT_SEARCH":
            if products_found:
                # Build response from found products
                product_names = [
                    f"{p.get('name', 'product')} (${p.get('price', 0):.2f})"
                    for p in products_found[:3]
                    if isinstance(p, dict)
                ]
                if product_names:
                    return f"I found some great options for you: {', '.join(product_names)}. Would you like to know more about any of these?"
            return "Let me help you find something great! We have amazing coffees, teas, and pastries. What are you in the mood for?"

        if intent == "GENERAL_CONVERSATION":
            return "Hey there! How can I help you today? I can help you find coffee, learn about our products, or even locate a store."

        # Default fallback
        return "I'm here to help! What can I get for you today?"

"""ADK Agent Orchestrator for Coffee Assistant System.

This module provides the main orchestrator class that manages the ADK agent system
using the proper ADK Runner pattern with our custom session service.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import TYPE_CHECKING, Any

import structlog
from google.adk import Runner
from google.genai import errors, types
from sqlspec.adapters.asyncpg.adk.store import AsyncpgADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

from app.config import db, db_manager, service_locator
from app.services.adk.agent import CoffeeAssistantAgent  # This now imports the router agent
from app.services.adk.tools import get_and_clear_timing_context, search_products_by_vector
from app.services.cache import CacheService
from app.services.metrics import MetricsService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.sessions import Session

logger = structlog.get_logger()

# HTTP Status codes
HTTP_SERVICE_UNAVAILABLE = 503


class ADKOrchestrator:
    """Main orchestrator for the ADK-based coffee assistant system.

    This class uses the proper ADK Runner pattern with SQLSpec session service
    for persistent session and event storage.
    """

    def __init__(self) -> None:
        """Initialize the ADK orchestrator with SQLSpec session service."""
        store = AsyncpgADKStore(config=db)
        self.session_service = SQLSpecSessionService(store)
        self.runner = Runner(
            agent=CoffeeAssistantAgent,
            app_name="coffee-assistant",
            session_service=self.session_service,
        )
        logger.debug("ADK Orchestrator initialized with SQLSpec session service")

    def _convert_markdown_to_html(self, text: str) -> str:
        """Convert simple markdown formatting to HTML."""
        if not text:
            return text

        # Convert **bold** to <strong>bold</strong>
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)

        # Convert *italic* to <em>italic</em>
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)

        # Convert numbered lists (1. item) to proper format
        lines = text.split("\n")
        in_list = False
        result_lines = []

        for line in lines:
            stripped = line.strip()
            if re.match(r"^\d+\.\s+", stripped):
                if not in_list:
                    result_lines.append("")  # Add space before list
                    in_list = True
                # Remove number and just keep the content
                item_text = re.sub(r"^\d+\.\s+", "", stripped)
                result_lines.append(item_text)
            else:
                if in_list and stripped:
                    in_list = False
                    result_lines.append("")  # Add space after list
                result_lines.append(line)

        return "\n".join(result_lines)

    async def process_request(
        self, query: str, user_id: str = "default", session_id: str | None = None, persona: str = "enthusiast"
    ) -> dict[str, Any]:
        """Process user request through ADK agent system with detailed timing."""
        start_time = time.time()
        timings = {}
        logger.debug("Processing request via ADK Runner...", query=query)

        try:
            # Time session management
            session_start = time.time()
            session = await self._ensure_session(user_id, session_id)
            timings["session_ms"] = round((time.time() - session_start) * 1000, 2)

            # Initialize cache variables
            from_cache = False
            event_data = None

            # Check cache first using database session
            cache_key = f"adk_response:{hash(query)}:{persona}"
            async with db_manager.provide_session(db) as cache_session:
                cache_service = service_locator.get(CacheService, cache_session)
                cached_response = await cache_service.get(cache_key)
                from_cache = cached_response is not None

                if cached_response:
                    logger.debug("Using cached response", cache_key=cache_key)
                    event_data = cached_response
                    timings["agent_processing_ms"] = 0  # No processing time for cached responses
                else:
                    # Time ADK agent processing
                    agent_start = time.time()
                    try:
                        events = await self._run_agent(query, user_id, session.id)
                        event_data = await self._process_events(events, query, timings)

                        # Check if the agent failed to follow workflow for PRODUCT_SEARCH
                        if event_data.get("intent_details", {}).get(
                            "intent"
                        ) == "PRODUCT_SEARCH" and not event_data.get("products_found"):
                            logger.warning("Agent failed workflow, retrying with reminder", query=query)
                            # Retry with workflow reminder
                            events_retry = await self._run_agent(query, user_id, session.id, retry_for_workflow=True)
                            event_data = await self._process_events(events_retry, query, timings)

                    except errors.ServerError as e:
                        # If all retries failed, return a graceful fallback
                        if getattr(e, "status", None) == HTTP_SERVICE_UNAVAILABLE:
                            logger.exception("ADK service unavailable after retries")
                            event_data = {
                                "final_response_text": "I apologize, but I'm experiencing some technical difficulties connecting to the AI service. Please try again in a moment.",
                                "agent_used": "Fallback",
                                "intent_details": {"intent": "GENERAL_CONVERSATION", "confidence": 0.0},
                                "search_details": {},
                                "products_found": [],
                            }
                        else:
                            raise
                    timings["agent_processing_ms"] = round((time.time() - agent_start) * 1000, 2)

                    # Only cache valid responses
                    # Don't cache if PRODUCT_SEARCH was detected but no products were found
                    should_cache = True
                    if event_data.get("intent_details", {}).get("intent") == "PRODUCT_SEARCH" and not event_data.get(
                        "products_found"
                    ):
                        logger.warning(
                            "Not caching incomplete PRODUCT_SEARCH response",
                            cache_key=cache_key,
                            intent="PRODUCT_SEARCH",
                            products_found=0,
                        )
                        should_cache = False

                    if should_cache:
                        await cache_service.set(cache_key, event_data, ttl=5)  # 5-minute TTL
                        logger.debug("Cached response", cache_key=cache_key)
                    else:
                        logger.debug("Skipped caching due to validation failure", cache_key=cache_key)

            # Get timing data from tool context
            tool_timings = get_and_clear_timing_context()
            if "intent_classification" in tool_timings:
                timings["intent_classification_ms"] = tool_timings["intent_classification"]["timing_ms"]
                # Update intent details with SQL query
                if event_data["intent_details"]:
                    event_data["intent_details"]["sql_query"] = tool_timings["intent_classification"]["sql_query"]
            if "vector_search" in tool_timings:
                timings["vector_search_ms"] = tool_timings["vector_search"]["total_ms"]
                timings["embedding_generation_ms"] = tool_timings["vector_search"]["embedding_ms"]
                timings["embedding_cache_hit"] = tool_timings["vector_search"]["embedding_cache_hit"]
                timings["vector_search_cache_hit"] = tool_timings["vector_search"]["vector_search_cache_hit"]
                # Update search details with actual data from tools
                event_data["search_details"].update({
                    "sql": tool_timings["vector_search"]["sql_query"],
                    "params": tool_timings["vector_search"]["params"],
                    "results_count": tool_timings["vector_search"]["results_count"],
                })

            total_time_ms = round((time.time() - start_time) * 1000, 2)
            timings["total_ms"] = total_time_ms

            debug_info = self._build_debug_info(event_data, timings, from_cache)

            # Record metrics with all timing components
            await self._record_metrics(session.id, query, event_data, timings)

            return self._build_success_response(
                event_data, session.id, total_time_ms, debug_info, user_id, persona, from_cache
            )

        except Exception as e:
            logger.exception("Request processing failed", error=str(e), query=query)
            return self._build_error_response(e, session_id, start_time, user_id, persona)

    async def _ensure_session(self, user_id: str, session_id: str | None) -> Session:
        """Ensure session exists using get-or-create pattern."""
        # Try to get existing session if session_id provided
        if session_id:
            existing = await self.session_service.get_session(
                app_name="coffee-assistant",
                user_id=user_id,
                session_id=session_id,
            )
            if existing:
                return existing

        # Create new session if not found or no session_id provided
        return await self.session_service.create_session(
            app_name="coffee-assistant",
            user_id=user_id,
            session_id=session_id,
            state={},
        )

    async def _run_agent(
        self, query: str, user_id: str, session_id: str, retry_for_workflow: bool = False
    ) -> AsyncGenerator:
        """Run the ADK agent with the user query with retry logic.

        Args:
            query: The user's query
            user_id: The user ID
            session_id: The session ID
            retry_for_workflow: If True, add a reminder about following the workflow
        """
        # Add workflow reminder if this is a retry for incomplete workflow
        if retry_for_workflow:
            reminder = (
                "\n\nREMINDER: You MUST follow the workflow exactly:\n"
                "1. Call classify_intent first\n"
                "2. If intent is PRODUCT_SEARCH, you MUST call search_products_by_vector\n"
                "Please process this query again following all steps: "
            )
            query_with_reminder = reminder + query
            content = types.Content(role="user", parts=[types.Part(text=query_with_reminder)])
            logger.warning("Retrying with workflow reminder", original_query=query)
        else:
            content = types.Content(role="user", parts=[types.Part(text=query)])

        # Retry logic for transient errors
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                return self.runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=content,
                )
            except errors.ServerError as e:
                # Check if it's a timeout or other retryable error
                if getattr(e, "status", None) == HTTP_SERVICE_UNAVAILABLE and attempt < max_retries - 1:
                    logger.warning(
                        "ADK request timed out, retrying...",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e),
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Last attempt or non-retryable error
                    raise
            except Exception:
                # Non-server errors should not be retried
                raise
        # This point should never be reached
        msg = "Failed to run agent after all retries"
        raise RuntimeError(msg)

    def _extract_text_from_event(self, event: Any) -> list[str]:
        """Extract text parts from an event."""
        if not (event.content and event.content.parts):
            return []
        return [part.text for part in event.content.parts if hasattr(part, "text") and part.text]

    def _should_filter_text(self, text: str) -> bool:
        """Check if text should be filtered out."""
        keywords = ["calling function", "function call", "tool call", "classify_intent", "search_products"]
        return any(keyword in text.lower() for keyword in keywords)

    def _process_intent_response(self, func_response: Any, timings: dict) -> dict[str, Any]:
        """Process intent classification response."""
        intent_result = func_response.response or {}
        logger.debug(
            "Intent classification result received",
            intent=intent_result.get("intent"),
            confidence=intent_result.get("confidence"),
        )
        if "timing_ms" in intent_result:
            timings["intent_classification_ms"] = intent_result["timing_ms"]

        return {
            "intent": intent_result.get("intent"),
            "confidence": intent_result.get("confidence"),
            "exemplar_used": intent_result.get("exemplar_phrase"),
        }

    def _process_search_response(self, func_response: Any, query: str) -> tuple[list, dict]:
        """Process product search response."""
        products_found = func_response.response or []
        search_details = {
            "query": query,
            "sql": """SELECT p.id, p.name, p.description, p.price,
       1 - (p.embedding <=> %s) as similarity
FROM product p
WHERE 1 - (p.embedding <=> %s) > %s
ORDER BY similarity DESC
LIMIT %s""",
            "params": {
                "similarity_threshold": 0.7,
                "limit": len(products_found) if isinstance(products_found, list) else 0,
            },
            "results_count": len(products_found) if isinstance(products_found, list) else 0,
        }
        return products_found, search_details

    def _generate_fallback_response(self, intent_details: dict, products_found: list) -> str:
        """Generate fallback response based on intent."""
        intent = intent_details.get("intent", "")
        if intent == "PRODUCT_SEARCH":
            if products_found:
                product_names = [p.get("name", "product") for p in products_found[:3] if isinstance(p, dict)]
                return f"I found these options for you: {', '.join(product_names)}. Would you like to know more?"
            return "Let me help you find something great! We have amazing coffees, teas, and pastries."
        if intent == "GENERAL_CONVERSATION":
            return "Hey there! What can I get you today?"
        return "I'm here to help! What can I get for you today?"

    async def _perform_fallback_search(self, query: str) -> tuple[list, str, dict]:
        """Perform a fallback product search when agent fails to follow workflow.

        Returns:
            Tuple of (products, response_text, timing_info)
        """
        try:
            # Import the search function and timing context getter

            # Perform the search directly
            logger.warning("Performing fallback search", query=query)
            products = await search_products_by_vector(query=query, limit=5, similarity_threshold=0.3)

            # Get the timing context from the search (including embedding_cache_hit)
            fallback_timing = get_and_clear_timing_context()

            if products and isinstance(products, list):
                # Build a response from the found products
                product_names = [
                    f"{p['name']} (${p['price']:.2f})"
                    for p in products[:3]
                    if isinstance(p, dict) and "name" in p and "price" in p
                ]

                if product_names:
                    response = f"I found some great options for you: {', '.join(product_names)}. Would you like to know more about any of these?"
                    return products, response, fallback_timing

        except Exception as e:
            logger.exception("Fallback search failed", error=str(e))
            return [], "I'd recommend our Hazelnut Haiku ($5.49) or Mocha Marvel ($5.99).", {}
        else:
            # If search failed or returned no products
            return [], "I'd recommend our Hazelnut Haiku ($5.49) or Mocha Marvel ($5.99).", fallback_timing

    async def _validate_and_apply_fallbacks(
        self, intent_details: dict, products_found: list, query: str, all_text_responses: list
    ) -> tuple[dict, list, str, dict]:
        """Validate intent and products, apply fallbacks if needed.

        Returns:
            Tuple of (intent_details, products_found, final_response_text, fallback_timing)
        """
        final_response_text = ""
        fallback_timing: dict[str, Any] = {}

        if not intent_details or not intent_details.get("intent"):
            logger.error("CRITICAL: Agent did NOT call classify_intent!", query=query)
            intent_details = {
                "intent": "GENERAL_CONVERSATION",
                "confidence": 0.0,
                "exemplar_used": "fallback - no classification performed",
            }
        elif intent_details.get("intent") == "PRODUCT_SEARCH" and not products_found:
            logger.error("CRITICAL: Agent detected PRODUCT_SEARCH but didn't search!", query=query)
            # Perform the search ourselves as a fallback
            products_found, final_response_text, fallback_timing = await self._perform_fallback_search(query)

        return intent_details, products_found, final_response_text, fallback_timing

    async def _process_events(self, events: AsyncGenerator, query: str, timings: dict) -> dict[str, Any]:
        """Process ADK events and extract relevant information with timing."""
        final_response_text = ""
        all_text_responses: list[str] = []
        agent_used = "ADK Multi-Agent"
        intent_details: dict[str, Any] = {}
        search_details: dict[str, Any] = {}
        products_found: list[Any] = []

        async for event in events:
            # Extract and filter text responses
            text_parts = self._extract_text_from_event(event)
            if text_parts:
                text_content = "".join(text_parts)
                if not self._should_filter_text(text_content):
                    all_text_responses.append(text_content)

            # Process final response
            if event.is_final_response() and text_parts:
                final_response_text = self._convert_markdown_to_html("".join(text_parts))
                agent_used = event.author or "ADK Multi-Agent"

            # Process function responses
            function_responses = event.get_function_responses()
            if function_responses:
                for func_response in function_responses:
                    if func_response.name == "classify_intent":
                        intent_details = self._process_intent_response(func_response, timings)
                    elif func_response.name == "search_products_by_vector":
                        products_found, search_details = self._process_search_response(func_response, query)

        # Validate and apply fallbacks
        intent_details, products_found, fallback_text, fallback_timing = await self._validate_and_apply_fallbacks(
            intent_details, products_found, query, all_text_responses
        )
        if fallback_text:
            final_response_text = fallback_text
            # Merge fallback timing into main timings if we did a fallback search
            if fallback_timing and "vector_search" in fallback_timing:
                timings["vector_search_ms"] = fallback_timing["vector_search"]["total_ms"]
                timings["embedding_generation_ms"] = fallback_timing["vector_search"]["embedding_ms"]
                timings["embedding_cache_hit"] = fallback_timing["vector_search"]["embedding_cache_hit"]
                # Update search details with fallback search info
                search_details.update({
                    "sql": fallback_timing["vector_search"]["sql_query"],
                    "params": fallback_timing["vector_search"]["params"],
                    "results_count": fallback_timing["vector_search"]["results_count"],
                })

        # Use collected responses if no final response
        if not final_response_text:
            if all_text_responses:
                logger.warning("No final response text found, using collected responses")
                final_response_text = self._convert_markdown_to_html(" ".join(all_text_responses))
            else:
                logger.error("No response text found in any events", query=query)
                final_response_text = self._generate_fallback_response(intent_details, products_found)

        return {
            "final_response_text": final_response_text,
            "agent_used": agent_used,
            "intent_details": intent_details,
            "search_details": search_details,
            "products_found": products_found,
        }

    def _build_debug_info(self, event_data: dict[str, Any], timings: dict, from_cache: bool = False) -> dict[str, Any]:
        """Build debug information with detailed timing breakdown."""
        return {
            "intent": event_data["intent_details"],
            "search": event_data["search_details"],
            "timings": {
                "total_ms": timings.get("total_ms", 0),
                "agent_processing_ms": timings.get("agent_processing_ms", 0),
                "session_ms": timings.get("session_ms", 0),
                "intent_classification_ms": timings.get("intent_classification_ms", 0),
                "vector_search_ms": timings.get("vector_search_ms", 0),
                "embedding_generation_ms": timings.get("embedding_generation_ms", 0),
                "embedding_cache_hit": timings.get("embedding_cache_hit", False),
            },
            "agent_used": event_data["agent_used"],
            "from_cache": from_cache,
        }

    async def _record_metrics(self, session_id: str, query: str, event_data: dict, timings: dict) -> None:
        """Record detailed metrics."""
        try:
            async with db_manager.provide_session(db) as session:
                metrics_service = service_locator.get(MetricsService, session)
                # Calculate average similarity score from products
                products = event_data.get("products_found", [])
                avg_similarity = 0.0
                if products:
                    similarity_scores = [
                        product["similarity_score"]
                        for product in products
                        if isinstance(product, dict) and "similarity_score" in product
                    ]

                    if similarity_scores:
                        avg_similarity = sum(similarity_scores) / len(similarity_scores)

                await metrics_service.record_search_metric(
                    session_id=session_id,  # Already a string from ADK
                    query_text=query,
                    intent=event_data.get("intent_details", {}).get("intent"),
                    confidence_score=event_data.get("intent_details", {}).get("confidence"),
                    vector_search_results=len(event_data.get("products_found", [])),
                    total_response_time_ms=int(timings.get("total_ms", 0)),  # Store as int in DB
                    vector_search_time_ms=int(timings.get("vector_search_ms", 0))
                    if timings.get("vector_search_ms")
                    else None,
                    llm_response_time_ms=int(timings.get("agent_processing_ms", 0))
                    if timings.get("agent_processing_ms")
                    else None,
                    embedding_generation_time_ms=int(timings.get("embedding_generation_ms", 0))
                    if timings.get("embedding_generation_ms")
                    else None,
                    embedding_cache_hit=timings.get("embedding_cache_hit", False),
                    vector_search_cache_hit=timings.get("vector_search_cache_hit", False),
                    intent_exemplar_used=event_data.get("intent_details", {}).get("exemplar_used"),
                    avg_similarity_score=avg_similarity,
                )
        except Exception:
            logger.exception("Failed to record metrics")

    def _build_success_response(
        self,
        event_data: dict[str, Any],
        session_id: str,
        total_time_ms: float,
        debug_info: dict[str, Any],
        user_id: str,
        persona: str,
        from_cache: bool = False,
    ) -> dict[str, Any]:
        """Build successful response dictionary."""
        return {
            "answer": event_data["final_response_text"],
            "products": event_data["products_found"],
            "agent_used": event_data["agent_used"],
            "session_id": session_id,
            "response_time_ms": total_time_ms,
            "debug_info": debug_info,
            "from_cache": from_cache,
            "metadata": {
                "user_id": user_id,
                "persona": persona,
            },
        }

    def _build_error_response(
        self,
        error: Exception,
        session_id: str | None,
        start_time: float,
        user_id: str,
        persona: str,
    ) -> dict[str, Any]:
        """Build error response dictionary."""
        return {
            "answer": "I apologize, but I'm experiencing some technical difficulties.",
            "intent": {"intent": "error"},
            "products": [],
            "agent_used": "ErrorFallback",
            "session_id": session_id,
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "error": str(error),
            "metadata": {"user_id": user_id, "persona": persona, "error_occurred": True},
        }

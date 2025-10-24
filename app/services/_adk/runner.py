"""ADK Agent Runner for the modern Coffee Assistant System.

This module provides the main runner class that manages the ADK agent system
using the proper ADK Runner pattern with our custom session service.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.genai import types
from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

from app.config import db, settings
from app.services._adk.monkey_patches import apply_genai_client_patch
from app.services._adk.tools import ALL_TOOLS
from app.services._persona_manager import BASE_SYSTEM_INSTRUCTION, PersonaManager

# Apply monkey patches for ADK library issues
apply_genai_client_patch()

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.sessions import Session

    from app.services._cache import CacheService

logger = structlog.get_logger()


class ADKRunner:
    """Main runner for the ADK-based coffee assistant system with persona support and response caching."""

    def __init__(self) -> None:
        """Initialize the ADK runner with SQLSpec session service."""
        store = OracleAsyncADKStore(config=db)
        self.session_service = SQLSpecSessionService(store)
        # Cache runners per persona to avoid recreating them
        self._persona_runners: dict[str, Runner] = {}
        logger.debug("ADKRunner initialized with SQLSpec session service")

    def _get_runner_for_persona(self, persona: str) -> Runner:
        """Get or create a Runner for the specified persona.

        Args:
            persona: The persona identifier ('novice', 'enthusiast', 'expert', 'barista')

        Returns:
            Runner configured for the specified persona
        """
        if persona not in self._persona_runners:
            # Create persona-specific agent
            persona_agent = LlmAgent(
                name="CoffeeAssistant",
                description=f"Coffee assistant with {persona} persona for Cymbal Coffee.",
                instruction=PersonaManager.get_system_prompt(persona, BASE_SYSTEM_INSTRUCTION),
                model=settings.vertex_ai.CHAT_MODEL,
                tools=ALL_TOOLS,
            )
            # Create runner for this persona
            # IMPORTANT: Use the same app_name for all personas to share sessions
            self._persona_runners[persona] = Runner(
                agent=persona_agent,
                app_name="coffee-assistant",  # Same for all personas
                session_service=self.session_service,  # Shared session service
            )
            logger.debug("Created Runner for persona: %s", persona)

        return self._persona_runners[persona]

    async def process_request(
        self,
        query: str,
        user_id: str = "default",
        session_id: str | None = None,
        persona: str = "enthusiast",
        cache_service: CacheService | None = None,
    ) -> dict[str, Any]:
        """Process user request through the ADK agent system with response caching."""
        start_time = time.time()
        logger.debug("Processing request via ADKRunner...", query=query, persona=persona)

        # Check response cache first (using query + persona as cache key)
        # This matches main branch behavior where persona affects responses
        cache_key = f"{query}|{persona}"
        from_cache = False
        if cache_service:
            cached = await cache_service.get_cached_response(cache_key=cache_key)
            logger.debug(
                "Cache lookup result",
                query_preview=query[:50],
                persona=persona,
                cached_found=cached is not None,
                cached_type=type(cached).__name__ if cached else None,
            )
            if cached:
                logger.info("Response cache hit", query_preview=query[:50], persona=persona, cache_id=cached.id)
                cached_response = cached.response_data
                cached_response["from_cache"] = True  # Mark as from cache
                return cached_response  # type: ignore[no-any-return]
            logger.debug("Response cache miss", query_preview=query[:50], persona=persona)

        session = await self._ensure_session(user_id, session_id)
        content = types.Content(role="user", parts=[types.Part(text=query)])

        # Get persona-specific runner
        runner = self._get_runner_for_persona(persona)

        agent_start = time.time()
        events = runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        )

        event_data = await self._process_events(events)
        agent_processing_ms = round((time.time() - agent_start) * 1000, 2)

        total_time_ms = round((time.time() - start_time) * 1000, 2)

        # Build response with all metadata
        response = {
            "answer": event_data["final_response_text"],
            "session_id": session.id,
            "response_time_ms": total_time_ms,
            "agent_processing_ms": agent_processing_ms,
            "intent_details": event_data.get("intent_details", {}),
            "search_details": event_data.get("search_details", {}),
            "products_found": event_data.get("products_found", []),
            "embedding_cache_hit": event_data.get("embedding_cache_hit", False),
            "intent_detected": event_data.get("intent_details", {}).get("intent", "GENERAL_CONVERSATION"),
            "from_cache": from_cache,
        }

        # Log detailed timing and cache information
        search_details = event_data.get("search_details", {})
        logger.info(
            "ADK request complete",
            query_preview=query[:50],
            total_ms=total_time_ms,
            agent_ms=agent_processing_ms,
            embedding_cache_hit=event_data.get("embedding_cache_hit", False),
            response_cache_hit=from_cache,
            intent=event_data.get("intent_details", {}).get("intent"),
            embedding_ms=search_details.get("embedding_ms", 0),
            search_ms=search_details.get("search_ms", 0),
            products_count=len(event_data.get("products_found", [])),
        )

        # Cache the response (5 minute TTL like main branch)
        if cache_service and event_data["final_response_text"]:
            try:
                result = await cache_service.set_cached_response(
                    cache_key=cache_key,
                    response_data=response,
                    ttl_minutes=5,
                )
                logger.info(
                    "Response cached successfully",
                    query_preview=query[:50],
                    cache_id=result.id if result else None,
                    cache_key=result.cache_key if result else None,
                )
            except Exception:
                logger.exception("Failed to cache response", query_preview=query[:50])

        return response

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

    async def _process_events(self, events: AsyncGenerator) -> dict[str, Any]:  # noqa: C901
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
                logger.info(
                    "Function responses detected",
                    count=len(function_responses),
                    functions=[f.name for f in function_responses],
                )
                for func_response in function_responses:
                    if func_response.name == "classify_intent":
                        intent_result = func_response.response or {}

                        # Debug: Log the classify_intent response
                        logger.debug(
                            "classify_intent response",
                            response_keys=list(intent_result.keys()),
                            has_embedding_cache_hit=("embedding_cache_hit" in intent_result),
                            embedding_cache_hit_value=intent_result.get("embedding_cache_hit"),
                        )

                        intent_details = {
                            "intent": intent_result.get("intent"),
                            "confidence": intent_result.get("confidence"),
                            "exemplar_phrase": intent_result.get("exemplar_phrase"),
                            "timing_ms": intent_result.get("timing_ms"),
                            "sql_query": intent_result.get("sql_query"),
                        }
                        # Track first embedding cache hit (for intent classification)
                        embedding_cache_hit_from_intent = intent_result.get("embedding_cache_hit", False)
                        if embedding_cache_hit_from_intent:
                            embedding_cache_hit = True
                            logger.info("Embedding cache HIT during intent classification")

                    elif func_response.name == "search_products_by_vector":
                        search_result = func_response.response or {}

                        # Debug: Log the full response structure
                        logger.debug(
                            "search_products_by_vector response",
                            response_keys=list(search_result.keys()),
                            has_timing=("timing" in search_result),
                            has_embedding_cache_hit=("embedding_cache_hit" in search_result),
                        )

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
                        # Track embedding cache hit from vector search
                        embedding_cache_hit_now = search_result.get("embedding_cache_hit", False)
                        if embedding_cache_hit_now:
                            embedding_cache_hit = True

                        # Log vector search details
                        logger.info(
                            "Vector search completed",
                            embedding_cache_hit=embedding_cache_hit_now,
                            embedding_ms=timing.get("embedding_ms", 0),
                            search_ms=timing.get("search_ms", 0),
                            products_found=len(products_found),
                        )

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

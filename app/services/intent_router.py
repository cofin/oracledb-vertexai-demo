"""Intent detection using Oracle 23AI native vector similarity search."""

from __future__ import annotations

import array
from typing import TYPE_CHECKING

import structlog

from app.config import INTENT_THRESHOLDS, VECTOR_SEARCH_CONFIG
from app.services.base import BaseService

if TYPE_CHECKING:
    import oracledb

    from app.services.embedding_cache import EmbeddingCache
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()
INTENT_EXEMPLARS = {
    "PRODUCT_RAG": [
        # Formal queries
        "What coffee do you recommend?",
        "Tell me about your espresso options",
        "I'm looking for a decaf drink",
        "What's your strongest coffee?",
        "Something sweet for the afternoon",
        "What pairs well with breakfast?",
        "Tell me about your seasonal drinks",
        "I need something with lots of caffeine",
        "What's the difference between a latte and cappuccino?",
        "Do you have any cold brew options?",
        "I want something with chocolate",
        "What's your most popular drink?",
        "Tell me about your coffee beans",
        "What's good for someone who doesn't like coffee?",
        "Do you have any sugar-free options?",
        # Casual/idiomatic expressions
        "I need something bold",
        "I need something strong",
        "caffeine please",
        "gimme anything",
        "what's good here?",
        "surprise me",
        "I'm tired, help",
        "need my fix",
        "hook me up",
        "what's brewing?",
        "hit me with your best shot",
        "I need to wake up",
        "something to get me going",
        "dealer's choice",
        "I'll take whatever",
        "just give me coffee",
        "anything with a kick",
        "make it strong",
        "double shot of anything",
        "I'm dragging today",
        "need some rocket fuel",
        "what's fresh?",
        "what do you got?",
        "coffee me",
        "bean juice please",
        # Typos and misspellings
        "coffe recommendations",
        "expresso options",
        "whats ur best seller",
        "capuccino or latte",
        "cold cofee options",
        "decaff drinks",
        # Context-specific
        "morning pick-me-up suggestions",
        "something to pair with dessert",
        "drinks for lactose intolerant",
        "coffee for studying late",
        "best drink for a hot day",
        "warming drinks for winter",
        # Multi-word entities
        "flat white vs cortado difference",
        "iced americano with oat milk",
        "vanilla latte extra shot",
        "caramel macchiato decaf",
        "matcha latte with almond milk",
        # Indirect queries
        "I'm sleepy what should I get",
        "first time here what's good",
        "help me choose something sweet",
        "I usually drink tea any suggestions",
        "not a coffee person what else",
        # Specific preferences
        "low calorie coffee options",
        "keto friendly drinks",
        "vegan drink options",
        "protein coffee choices",
        "organic coffee selections",
        "i need something light",
    ],
    "GENERAL_CONVERSATION": [
        # Greetings and pleasantries
        "How are you today?",
        "Tell me a coffee joke",
        "What's your name?",
        "Thanks for your help",
        "That sounds great",
        "Can you help me?",
        "Hello",
        "Good morning",
        "Goodbye",
        "What can you do?",
        "Tell me about yourself",
        "That's interesting",
        "I see",
        "Never mind",
        "Sorry",
        "hey",
        "sup",
        "yo",
        "what's up",
        "howdy",
        "hi",
        "hi there",
        "thanks",
        "cool",
        "awesome",
        "bye",
        "see ya",
        "later",
        "cheers",
        # Conversational
        "how's it going",
        "nice to meet you",
        "have a great day",
        "take care",
        "appreciate it",
        "sounds good",
        "got it",
        "makes sense",
        # Feedback
        "that was helpful",
        "great suggestion",
        "not what I was looking for",
        "can you try again",
        "love this place",
        # Meta questions
        "are you a bot",
        "are you real",
        "who made you",
        "how do you work",
    ],
}


class IntentRouter(BaseService):
    """Oracle 23AI native vector similarity search for intent routing."""

    def __init__(
        self,
        connection: oracledb.AsyncConnection,
        vertex_ai_service: VertexAIService,
        embedding_cache: EmbeddingCache | None = None,
    ) -> None:
        """Initialize with Vertex AI service and optional embedding cache."""
        super().__init__(connection)
        self.vertex_ai = vertex_ai_service
        self.cache = embedding_cache

    async def route_intent(self, query: str) -> tuple[list[tuple[str, float, str]], bool]:
        """Route intent using Oracle's native vector similarity search.

        Args:
            query: User's input query

        Returns:
            Tuple of (results, embedding_cache_hit) where results is a list of tuples (intent, confidence_score, matched_phrase)
        """
        # Get embedding (with caching if available)
        embedding_cache_hit = False
        if self.cache:
            query_embedding, embedding_cache_hit = await self.cache.get_embedding(query, self.vertex_ai)
        else:
            query_embedding = await self.vertex_ai.create_embedding(query)

        oracle_vector = array.array("f", query_embedding)

        # Execute pure vector similarity search
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT
                    intent,
                    phrase,
                    1 - VECTOR_DISTANCE(embedding, :query_embedding, COSINE) AS similarity_score
                FROM intent_exemplar
                WHERE 1 - VECTOR_DISTANCE(embedding, :query_embedding, COSINE) > :min_threshold
                ORDER BY similarity_score DESC
                FETCH FIRST :top_k ROWS ONLY
                """,
                {
                    "query_embedding": oracle_vector,
                    "min_threshold": VECTOR_SEARCH_CONFIG["min_vector_threshold"],
                    "top_k": VECTOR_SEARCH_CONFIG["final_top_k"],
                },
            )

            results = await cursor.fetchall()

            # Filter by per-intent thresholds and return
            filtered_results = [
                (row[0], row[2], row[1])  # (intent, score, phrase)
                for row in results
                if row[2] >= INTENT_THRESHOLDS.get(row[0], 0.70)
            ]

            # Log search results for debugging
            logger.info(
                "vector_search_results",
                query=query,
                total_results=len(results),
                filtered_results=len(filtered_results),
                top_match=filtered_results[0] if filtered_results else None,
            )

            return filtered_results, embedding_cache_hit

    async def route_intent_single(self, query: str) -> tuple[str, float, str, bool]:
        """Route to single best intent with fallback to GENERAL_CONVERSATION.

        Args:
            query: User's input query

        Returns:
            Tuple of (intent, confidence_score, matched_phrase, embedding_cache_hit)
        """
        # Use pure vector similarity search
        results, embedding_cache_hit = await self.route_intent(query)

        if results:
            return (*results[0], embedding_cache_hit)
        # No matches above threshold - default to general conversation
        return "GENERAL_CONVERSATION", 0.0, "", embedding_cache_hit

    async def route_with_llm_fallback(
        self,
        query: str,
        high_confidence_threshold: float = 0.9,
        medium_confidence_threshold: float = 0.7,
    ) -> tuple[str, float, str]:
        """Route with LLM fallback for medium-confidence queries.

        Args:
            query: User's input query
            high_confidence_threshold: Threshold for direct routing
            medium_confidence_threshold: Threshold for LLM escalation

        Returns:
            Tuple of (intent, confidence_score, method_used)
        """
        # First, try vector similarity search
        intent, confidence, _, _ = await self.route_intent_single(query)

        if confidence > high_confidence_threshold:
            # High confidence - use vector search result directly
            return intent, confidence, "vector"
        if confidence > medium_confidence_threshold:
            # Medium confidence - escalate to LLM
            llm_intent = await self._llm_classify(query)
            return llm_intent, confidence, "llm_fallback"
        # Low confidence - default to general conversation
        return "GENERAL_CONVERSATION", confidence, "default"

    async def _llm_classify(self, query: str) -> str:
        """Use LLM for zero-shot intent classification.

        Args:
            query: User's input query

        Returns:
            Classified intent
        """
        prompt = f"""You are an intent classifier for a coffee shop chatbot.
Classify this query into exactly one category:
- PRODUCT_RAG: Questions about coffee, drinks, food, menu items, or recommendations
- GENERAL_CONVERSATION: Greetings, thanks, general chat, or off-topic questions

Respond with only the category name and nothing else.

Query: "{query}"
Category:"""

        try:
            response, _ = await self.vertex_ai.generate_content(prompt)

            # Extract the intent from response
            intent = response.strip().upper()

            # Validate the response
            if intent in ["PRODUCT_RAG", "GENERAL_CONVERSATION"]:
                return intent

        except Exception:
            logger.exception("llm_classification_error", query=query)

        # On any error or invalid response, default to general conversation
        return "GENERAL_CONVERSATION"

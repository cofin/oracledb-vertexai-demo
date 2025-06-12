"""Intent detection using semantic similarity with pre-computed exemplar embeddings."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import structlog
from sklearn.metrics.pairwise import cosine_similarity

if TYPE_CHECKING:
    from app.services.intent_exemplar import IntentExemplarService
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class IntentRouter:
    """Routes user queries to appropriate handlers using semantic similarity."""

    # Intent exemplars for semantic matching
    INTENT_EXEMPLARS = {
        "PRODUCT_RAG": [
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
        ],
        "LOCATION_RAG": [
            "Where are your coffee shops?",
            "Find a store near downtown",
            "What are your hours?",
            "Is there a location on Main Street?",
            "Which shops have parking?",
            "Closest cafe to the university",
            "Are you open on weekends?",
            "Do you have outdoor seating?",
            "Which location is biggest?",
            "Find me the nearest store",
            "What time do you close?",
            "Are there any 24-hour locations?",
        ],
        "GENERAL_CONVERSATION": [
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
        ],
    }

    def __init__(
        self,
        vertex_ai_service: VertexAIService,
        exemplar_service: IntentExemplarService | None = None,
    ) -> None:
        """Initialize with a Vertex AI service instance and optional exemplar service."""
        self.vertex_ai = vertex_ai_service
        self.exemplar_service = exemplar_service
        self.exemplar_embeddings: dict[str, np.ndarray] = {}
        self.exemplar_phrases: dict[str, list[str]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Load cached embeddings or compute them if not cached."""
        if self._initialized:
            return

        if self.exemplar_service:
            # Try to load from cache first
            logger.info("Loading cached intent exemplar embeddings...")
            cached_data = await self.exemplar_service.get_exemplars_with_phrases()

            if cached_data:
                # Use cached embeddings
                for intent, phrase_embeddings in cached_data.items():
                    phrases = []
                    embeddings = []
                    for phrase, embedding in phrase_embeddings:
                        phrases.append(phrase)
                        embeddings.append(embedding)

                    self.exemplar_phrases[intent] = phrases
                    self.exemplar_embeddings[intent] = np.array(embeddings)

                logger.info("Loaded %d cached embeddings", sum(len(v) for v in self.exemplar_embeddings.values()))
                self._initialized = True
                return

            # Cache is empty, populate it
            logger.info("Populating intent exemplar cache...")
            await self.exemplar_service.populate_cache(
                self.INTENT_EXEMPLARS,
                self.vertex_ai,
            )

            # Load the newly cached data
            cached_data = await self.exemplar_service.get_exemplars_with_phrases()
            for intent, phrase_embeddings in cached_data.items():
                phrases = []
                embeddings = []
                for phrase, embedding in phrase_embeddings:
                    phrases.append(phrase)
                    embeddings.append(embedding)

                self.exemplar_phrases[intent] = phrases
                self.exemplar_embeddings[intent] = np.array(embeddings)
        else:
            # No cache service, compute embeddings directly (fallback)
            logger.warning("No exemplar cache service provided, computing embeddings on demand")
            for intent, phrases in self.INTENT_EXEMPLARS.items():
                embeddings = []
                self.exemplar_phrases[intent] = phrases

                # Process phrases in batches for efficiency
                for phrase in phrases:
                    embedding = await self.vertex_ai.create_embedding(phrase)
                    embeddings.append(embedding)

                self.exemplar_embeddings[intent] = np.array(embeddings)

        self._initialized = True

    async def route_intent(self, query: str, threshold: float = 0.75) -> tuple[str, float, str]:
        """Route a query to an intent based on semantic similarity.

        Args:
            query: User's input query
            threshold: Minimum similarity score to consider a match

        Returns:
            Tuple of (intent, confidence_score, most_similar_exemplar)
        """
        if not self._initialized:
            await self.initialize()

        # Get embedding for the query
        query_embedding = await self.vertex_ai.create_embedding(query)

        best_score = -1
        best_intent = "GENERAL_CONVERSATION"
        best_exemplar = ""

        # Compare against all exemplars
        for intent, exemplar_embeddings in self.exemplar_embeddings.items():
            # Calculate cosine similarity with all exemplars for this intent
            similarities = cosine_similarity([query_embedding], exemplar_embeddings)[0]  # pyright: ignore

            # Find the best match for this intent
            max_idx = similarities.argmax()
            max_score = similarities[max_idx]

            if max_score > best_score:
                best_score = max_score
                best_intent = intent
                # Use stored phrases if available, otherwise fall back to INTENT_EXEMPLARS
                if intent in self.exemplar_phrases:
                    best_exemplar = self.exemplar_phrases[intent][max_idx]
                else:
                    best_exemplar = self.INTENT_EXEMPLARS[intent][max_idx]

        # Apply threshold - if below threshold, default to general conversation
        if best_score < threshold:
            return "GENERAL_CONVERSATION", best_score, best_exemplar

        return best_intent, best_score, best_exemplar

    async def route_with_fallback(
        self, query: str, high_confidence_threshold: float = 0.9, medium_confidence_threshold: float = 0.7
    ) -> tuple[str, float, str]:
        """Route with LLM fallback for medium-confidence queries.

        Args:
            query: User's input query
            high_confidence_threshold: Threshold for direct routing
            medium_confidence_threshold: Threshold for LLM escalation

        Returns:
            Tuple of (intent, confidence_score, method_used)
        """
        # First, try semantic similarity
        intent, confidence, exemplar = await self.route_intent(query)

        if confidence > high_confidence_threshold:
            # High confidence - use embedding result directly
            return intent, confidence, "embedding"
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
- LOCATION_RAG: Questions about store locations, hours, addresses, or directions
- GENERAL_CONVERSATION: Greetings, thanks, general chat, or off-topic questions

Respond with only the category name and nothing else.

Query: "{query}"
Category:"""

        try:
            response = await self.vertex_ai.generate_content(prompt)

            # Extract the intent from response
            intent = response.strip().upper()

            # Validate the response
            if intent in ["PRODUCT_RAG", "LOCATION_RAG", "GENERAL_CONVERSATION"]:
                return intent
            # Fallback if LLM doesn't follow instructions

        except Exception:  # noqa: BLE001
            # On any error, default to general conversation
            return "GENERAL_CONVERSATION"
        return "GENERAL_CONVERSATION"

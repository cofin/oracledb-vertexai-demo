"""Intent exemplars for semantic intent routing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.schemas import IntentResult, SimilarIntent
from app.services.base import SQLSpecService

if TYPE_CHECKING:
    from sqlspec import AsyncDriverAdapterBase

    from app.services._exemplar import ExemplarService
    from app.services._vertex_ai import VertexAIService

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
    "STORE_LOCATION": [
        # Direct location queries
        "Where are your stores?",
        "Find stores near me",
        "What locations do you have?",
        "Store locations",
        "Where can I find you?",
        "Do you have a store in Seattle?",
        "Are there any stores in California?",
        "Show me stores in Portland",
        "Store finder",
        "Which cities do you operate in?",
        # Hours queries
        "What time do you open?",
        "Store hours",
        "When do you close?",
        "Are you open now?",
        "What are your hours?",
        "Opening hours",
        "When does the downtown store open?",
        "Hours of operation",
        "Business hours",
        "Are you open on weekends?",
        "Sunday hours",
        "Holiday hours",
        # Address and contact queries
        "What's your address?",
        "Store address",
        "How do I get there?",
        "What's the phone number?",
        "Store contact info",
        "How can I reach you?",
        "Where is the nearest location?",
        "Closest store to me",
        "Store phone number",
        # Specific location queries
        "Stores in downtown Portland",
        "Seattle locations",
        "San Francisco stores",
        "Oakland coffee shops",
        "Portland Pearl District location",
        "Where in California?",
        "Oregon stores",
        "Washington locations",
        # Casual/conversational
        "where are you located?",
        "where can I visit?",
        "got any stores nearby?",
        "how do I find you?",
        "what time you guys open?",
        "you open today?",
        "still open?",
        "what's your address?",
        "can I call the store?",
        "where's the closest one?",
        # Typos and variations
        "store locationz",
        "wher are you",
        "store ours",
        "wat time open",
        "addres please",
        "stores neer me",
        "loctions",
        # Intent combinations
        "Do you have a store in Seattle and what are the hours?",
        "Find me a store in Portland and give me the address",
        "Where's the nearest location and when do you open?",
        "Store hours for downtown location",
        "Seattle store phone number",
        "Address for Portland store",
        # Direction-focused
        "How to get to your store",
        "Directions to nearest location",
        "Where exactly are you?",
        "Map to store",
        # Availability queries
        "Do you have locations in my area?",
        "Are there stores near downtown?",
        "Any locations close by?",
        "Where's your nearest shop?",
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
        "thanks",
        "thank you",
        "appreciate it",
        "cool",
        "nice",
        "awesome",
        "perfect",
    ],
}

logger = structlog.get_logger()


class IntentService(SQLSpecService):
    """PostgreSQL native vector similarity search for intent routing."""

    def __init__(
        self,
        driver: AsyncDriverAdapterBase,
        exemplar_service: ExemplarService,
        vertex_ai_service: VertexAIService,
    ) -> None:
        """Initialize intent service."""
        super().__init__(driver)
        self.exemplar_service = exemplar_service
        self.vertex_ai_service = vertex_ai_service

    async def search_similar_intents(
        self,
        query_embedding: list[float],
        min_threshold: float,
        limit: int,
    ) -> list[SimilarIntent]:
        """Search for similar intents in the exemplar table."""
        return await self.driver.select(
            """
            SELECT
                intent AS "intent",
                phrase AS "phrase",
                1 - VECTOR_DISTANCE(embedding, :query_embedding, COSINE) AS "similarity",
                confidence_threshold AS "confidence_threshold"
            FROM intent_exemplar
            WHERE 1 - VECTOR_DISTANCE(embedding, :query_embedding, COSINE) > :min_threshold
            ORDER BY "similarity" DESC
            FETCH FIRST :limit ROWS ONLY
            """,
            query_embedding=query_embedding,
            min_threshold=min_threshold,
            limit=limit,
            schema_type=SimilarIntent,
        )

    async def increment_usage_by_phrase(self, intent: str, phrase: str) -> None:
        """Increment the usage count for a given exemplar."""
        await self.driver.execute(
            """
            UPDATE intent_exemplar
            SET usage_count = usage_count + 1
            WHERE intent = :intent AND phrase = :phrase
            """,
            intent=intent,
            phrase=phrase,
        )

    async def classify_intent(
        self,
        query: str,
        user_embedding: list[float] | None = None,
        min_threshold: float = 0.6,
        max_results: int = 5,
    ) -> IntentResult:
        """Classify intent using vector similarity with exemplars."""
        if user_embedding is None:
            user_embedding, embedding_cache_hit = await self.vertex_ai_service.get_text_embedding(
                query, return_cache_status=True
            )
        else:
            embedding_cache_hit = True

        similar_intents = await self.search_similar_intents(
            query_embedding=user_embedding,
            min_threshold=min_threshold,
            limit=max_results,
        )

        if not similar_intents:
            return IntentResult(
                intent="GENERAL_CONVERSATION",
                confidence=0.0,
                exemplar_phrase="",
                embedding_cache_hit=embedding_cache_hit,
                fallback_used=True,
            )

        best_match = similar_intents[0]

        if best_match.similarity >= best_match.confidence_threshold:
            await self.increment_usage_by_phrase(best_match.intent, best_match.phrase)

            return IntentResult(
                intent=best_match.intent,
                confidence=best_match.similarity,
                exemplar_phrase=best_match.phrase,
                embedding_cache_hit=embedding_cache_hit,
                fallback_used=False,
            )

        return IntentResult(
            intent="GENERAL_CONVERSATION",
            confidence=best_match.similarity,
            exemplar_phrase=best_match.phrase,
            embedding_cache_hit=embedding_cache_hit,
            fallback_used=True,
        )

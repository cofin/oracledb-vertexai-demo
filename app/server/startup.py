"""Application startup hooks for initializing services and caching."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

import structlog

from app import config
from app.services.intent_exemplar import IntentExemplarService
from app.services.product import ProductService
from app.services.vertex_ai import VertexAIService

if TYPE_CHECKING:
    import oracledb
    from litestar import Litestar

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


async def populate_product_exemplars(
    conn: oracledb.AsyncConnection, exemplar_service: IntentExemplarService, vertex_ai_service: VertexAIService
) -> None:
    """Add all product names as PRODUCT_RAG exemplars."""
    logger.info("Adding product names as exemplars...")

    # Get all products
    from app.db.repositories.product import ProductRepository

    product_repository = ProductRepository(conn)
    product_service = ProductService(product_repository)
    products = await product_service.get_all()

    # Create exemplars from product names
    product_exemplars = []
    for product in products:
        name = product.name
        # Add various query patterns for each product
        product_exemplars.extend([
            f"tell me about {name}",
            f"what's in the {name}",
            f"how much is {name}",
            f"{name} price",
            f"{name} information",
            f"I want {name}",
            name,  # Just the product name itself
        ])

    # Add product exemplars
    count = 0
    for exemplar in product_exemplars:
        # Check if already exists
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                SELECT 1 FROM intent_exemplar
                WHERE intent = :intent AND phrase = :phrase
                """,
                {"intent": "PRODUCT_RAG", "phrase": exemplar},
            )
            exists = await cursor.fetchone()

            if not exists:
                # Generate embedding
                embedding = await vertex_ai_service.create_embedding(exemplar)
                await exemplar_service.cache_exemplar("PRODUCT_RAG", exemplar, embedding)
                count += 1

                if count % 10 == 0:
                    logger.info("Added %d product exemplars...", count)

    logger.info("Added %d new product exemplars", count)


async def initialize_intent_exemplar_cache(app: Litestar) -> None:
    """Initialize the intent exemplar cache on startup to avoid delays on first request."""
    logger.info("Starting intent exemplar cache initialization...")

    # Get Oracle connection from the async pool
    async with config.oracle_async.get_connection() as conn:
        # Create service instances
        from app.db.repositories.intent_exemplar import IntentExemplarRepository

        vertex_ai_service = VertexAIService()
        exemplar_repository = IntentExemplarRepository(conn)
        exemplar_service = IntentExemplarService(exemplar_repository)
        cached_data = await exemplar_service.get_exemplars_with_phrases()
        if not cached_data:
            logger.info("Populating intent exemplar cache...")
            await exemplar_service.populate_cache(INTENT_EXEMPLARS, vertex_ai_service)
            logger.info("Intent exemplar cache populated successfully")
        else:
            logger.info(
                "Intent exemplar cache already populated",
                exemplar_count=sum(len(v) for v in cached_data.values()),
            )

        # Add product names as exemplars
        await populate_product_exemplars(conn, exemplar_service, vertex_ai_service)


async def warm_up_connection_pool(app: Litestar) -> None:
    """Warm up the Oracle connection pool to avoid cold start delays."""
    logger.info("Warming up Oracle connection pool...")

    # Run a simple query to establish pool connections
    async with config.oracle_async.get_connection() as conn, conn.cursor() as cursor:
        await cursor.execute("SELECT 1 FROM DUAL")
        await cursor.fetchone()

    logger.info("Connection pool warmed up")


async def on_startup(app: Litestar) -> None:
    """Main startup hook that runs all initialization tasks."""

    logger.info("Running application startup tasks...")

    app.state.csp_nonce_generator = lambda: secrets.token_urlsafe(16)

    await warm_up_connection_pool(app)
    await initialize_intent_exemplar_cache(app)
    logger.info("Application startup complete")

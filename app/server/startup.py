"""Application startup hooks for initializing services and caching."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

import structlog

from app import config
from app.server import deps
from app.services.exemplar import ExemplarService
from app.services.intent import INTENT_EXEMPLARS
from app.services.product import ProductService

if TYPE_CHECKING:
    from litestar import Litestar

    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()

# Intent exemplars for semantic matching


async def populate_product_exemplars(
    product_service: ProductService, exemplar_service: ExemplarService, vertex_ai_service: VertexAIService
) -> None:
    """Add all product names as PRODUCT_RAG exemplars."""
    logger.info("Adding product names as exemplars...")

    # Get all products
    products = await product_service.get_all()

    # Create exemplars from product names
    product_exemplars = []
    for product in products:
        name = product["name"]
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
        # Check if already exists using driver
        result = await exemplar_service.driver.select_one_or_none(
            """
            SELECT 1 FROM intent_exemplar
            WHERE intent = :intent AND phrase = :phrase
            """,
            {"intent": "PRODUCT_RAG", "phrase": exemplar},
        )

        if not result:
            # Generate embedding
            embedding = await vertex_ai_service.get_text_embedding(exemplar)
            await exemplar_service.cache_exemplar("PRODUCT_RAG", exemplar, embedding)
            count += 1

            if count % 10 == 0:
                logger.info("Added %d product exemplars...", count)

    logger.info("Added %d new product exemplars", count)


async def initialize_intent_exemplar_cache(app: Litestar) -> None:
    """Initialize the intent exemplar cache on startup to avoid delays on first request."""
    logger.info("Starting intent exemplar cache initialization...")

    # Get Oracle connection from the async pool
    async with config.db_manager.provide_session(config.db) as driver:
        # Create service instances
        vertex_ai_service = await anext(deps.provide_vertex_ai_service())
        exemplar_service = ExemplarService(driver)
        product_service = ProductService(driver)

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
        await populate_product_exemplars(product_service, exemplar_service, vertex_ai_service)


async def warm_up_connection_pool(app: Litestar) -> None:
    """Warm up the Oracle connection pool to avoid cold start delays."""
    logger.info("Warming up Oracle connection pool...")

    # Run a simple query to establish pool connections
    async with config.db_manager.provide_session(config.db) as driver:
        await driver.execute("SELECT 1 FROM DUAL")

    logger.info("Connection pool warmed up")


async def on_startup(app: Litestar) -> None:
    """Main startup hook that runs all initialization tasks."""

    logger.info("Running application startup tasks...")

    app.state.csp_nonce_generator = lambda: secrets.token_urlsafe(16)

    await warm_up_connection_pool(app)
    await initialize_intent_exemplar_cache(app)
    logger.info("Application startup complete")

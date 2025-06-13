"""Application startup hooks for initializing services and caching."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app import config
from app.server import deps
from app.services.intent_exemplar import IntentExemplarService
from app.services.intent_router import INTENT_EXEMPLARS, IntentRouter

if TYPE_CHECKING:
    from litestar import Litestar

logger = structlog.get_logger()


async def initialize_intent_exemplar_cache(app: Litestar) -> None:
    """Initialize the intent exemplar cache on startup to avoid delays on first request."""
    logger.info("Starting intent exemplar cache initialization...")

    # Get Oracle connection from the async pool
    async with config.oracle_async.get_connection() as conn:
        # Create service instances
        vertex_ai_service = await anext(deps.provide_vertex_ai_service())
        exemplar_service = IntentExemplarService(conn)
        intent_router = IntentRouter(vertex_ai_service, exemplar_service)
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

        # Ensure the router is initialized (loads embeddings into memory)
        await intent_router.initialize()
        logger.info("Intent router initialized successfully")


async def warm_up_connection_pool(app: Litestar) -> None:
    """Warm up the Oracle connection pool to avoid cold start delays."""
    logger.info("Warming up Oracle connection pool...")

    # Run a simple query to establish pool connections
    async with config.oracle_async.get_connection() as conn:
        cursor = conn.cursor()
        try:
            await cursor.execute("SELECT 1 FROM DUAL")
            await cursor.fetchone()
        finally:
            cursor.close()

    logger.info("Connection pool warmed up")


async def on_startup(app: Litestar) -> None:
    """Main startup hook that runs all initialization tasks."""

    logger.info("Running application startup tasks...")
    await warm_up_connection_pool(app)
    await initialize_intent_exemplar_cache(app)
    logger.info("Application startup complete")

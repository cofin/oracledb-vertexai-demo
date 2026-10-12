# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Scheduled background maintenance tasks for the system domain."""

from __future__ import annotations

import structlog
from litestar_queues import task

from app.domain.system.services import CacheService
from app.lib.jobs import task_container_scope

__all__ = ("cleanup_expired_cache_and_sessions",)

logger = structlog.get_logger()


@task(
    "system.cache_cleanup",
    queue="maintenance",
    cron="*/15 * * * *",
    unique_by="task",
    description="Prune expired response_cache entries and stale agent_session rows.",
)
async def cleanup_expired_cache_and_sessions(retention_days: int = 7) -> dict[str, int]:
    """Delete expired response-cache rows and stale agent sessions.

    Args:
        retention_days: Retention threshold in days for idle ``agent_session`` records.

    Returns:
        Summary dictionary with deleted row counts.
    """
    async with task_container_scope() as container:
        cache_service = await container.get(CacheService)
        expired_responses = await cache_service.delete_expired_responses()
        stale_sessions = await cache_service.delete_stale_agent_sessions(retention_days=retention_days)

    logger.info(
        "Completed scheduled system cache cleanup",
        expired_responses_deleted=expired_responses,
        stale_sessions_deleted=stale_sessions,
        retention_days=retention_days,
    )
    return {"expired_responses_deleted": expired_responses, "stale_sessions_deleted": stale_sessions}

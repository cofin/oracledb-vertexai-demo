# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import delete, func, select

from app.db import models as m

if TYPE_CHECKING:
    from uuid import UUID

    from app.schemas import SearchMetricsCreate


class UserSessionService(SQLAlchemyAsyncRepositoryService[m.UserSession]):
    """Oracle session management with Advanced Alchemy."""

    class Repo(SQLAlchemyAsyncRepository[m.UserSession]):
        """Session repository."""

        model_type = m.UserSession

    repository_type = Repo
    match_fields = ["session_id"]

    async def to_model(self, data: Any, operation: str | None = None) -> m.UserSession:
        """Convert data dictionary to model instance."""
        if isinstance(data, dict) and operation == "create" and "session_id" not in data:
            data["session_id"] = str(uuid.uuid4())
        return await super().to_model(data, operation)

    async def create_session(self, user_id: str, ttl_hours: int = 24) -> m.UserSession:
        """Create new session with automatic expiry."""
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

        return await self.create({
            "session_id": session_id,
            "user_id": user_id,
            "data": {},
            "expires_at": expires_at,
        })

    async def get_active_session(self, session_id: str) -> m.UserSession | None:
        """Get session if not expired."""
        session = await self.get_one_or_none(session_id=session_id)
        if session and session.expires_at > datetime.now(UTC):
            return session
        return None

    async def update_session_data(self, session_id: str, data: dict) -> m.UserSession:
        """Update session data."""
        session = await self.get_active_session(session_id)
        if not session:
            msg = "Session not found or expired"
            raise ValueError(msg)

        # Merge with existing data
        updated_data = {**session.data, **data}
        # Following litestar-fullstack pattern: update expects dict with id
        return await self.update({"id": session.id, "data": updated_data})

    async def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        now = datetime.now(UTC)
        stmt = delete(m.UserSession).where(m.UserSession.expires_at < now)
        result = await self.repository.session.execute(stmt)
        await self.repository.session.commit()
        return result.rowcount or 0


class ChatConversationService(SQLAlchemyAsyncRepositoryService[m.ChatConversation]):
    """Conversation history with Advanced Alchemy."""

    class Repo(SQLAlchemyAsyncRepository[m.ChatConversation]):
        """Conversation repository."""

        model_type = m.ChatConversation

    repository_type = Repo

    async def add_message(
        self,
        session_id: UUID,
        user_id: str,
        role: str,
        content: str,
        message_metadata: dict | None = None,
    ) -> m.ChatConversation:
        """Add message to conversation."""
        return await self.create({
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "message_metadata": message_metadata or {},
        })

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        session_id: UUID | None = None,
    ) -> list[m.ChatConversation]:
        """Get recent conversation history."""
        filters = [m.ChatConversation.user_id == user_id]
        if session_id:
            filters.append(m.ChatConversation.session_id == session_id)

        result = await self.list(
            statement=select(m.ChatConversation)
            .where(*filters)
            .order_by(m.ChatConversation.created_at.desc())
            .limit(limit),
        )
        return list(result)


class ResponseCacheService(SQLAlchemyAsyncRepositoryService[m.ResponseCache]):
    """Oracle response caching with Advanced Alchemy."""

    class Repo(SQLAlchemyAsyncRepository[m.ResponseCache]):
        """Cache repository."""

        model_type = m.ResponseCache

    repository_type = Repo
    match_fields = ["cache_key"]

    def _generate_cache_key(self, query: str, user_id: str = "default") -> str:
        """Generate deterministic cache key."""
        content = f"{query.lower().strip()}:{user_id}"
        return hashlib.sha256(content.encode()).hexdigest()  # Use SHA256 instead of MD5

    async def get_cached_response(self, query: str, user_id: str = "default") -> dict | None:
        """Get cached response if not expired."""
        cache_key = self._generate_cache_key(query, user_id)
        now = datetime.now(UTC)

        cached = await self.get_one_or_none(cache_key=cache_key)
        if cached and cached.expires_at > now:
            # Increment hit count
            # Update hit count using dict with id
            await self.update({"id": cached.id, "hit_count": cached.hit_count + 1})
            return cached.response
        return None

    async def cache_response(
        self,
        query: str,
        response: dict,
        ttl_minutes: int = 5,
        user_id: str = "default",
    ) -> m.ResponseCache:
        """Cache response with TTL."""
        cache_key = self._generate_cache_key(query, user_id)
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)

        # Use upsert pattern
        existing = await self.get_one_or_none(cache_key=cache_key)
        if existing:
            # Update existing cache entry
            return await self.update({
                "id": existing.id,
                "response": response,
                "expires_at": expires_at,
                "query_text": query,
            })
        return await self.create({
            "cache_key": cache_key,
            "query_text": query,
            "response": response,
            "expires_at": expires_at,
            "hit_count": 0,
        })

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        now = datetime.now(UTC)
        stmt = delete(m.ResponseCache).where(m.ResponseCache.expires_at < now)
        result = await self.repository.session.execute(stmt)
        await self.repository.session.commit()
        return result.rowcount or 0


class SearchMetricsService(SQLAlchemyAsyncRepositoryService[m.SearchMetrics]):
    """Search performance metrics with Advanced Alchemy."""

    class Repo(SQLAlchemyAsyncRepository[m.SearchMetrics]):
        """Metrics repository."""

        model_type = m.SearchMetrics

    repository_type = Repo

    async def record_search(self, metrics_data: SearchMetricsCreate) -> m.SearchMetrics:
        """Record search performance metrics."""
        return await self.create(metrics_data, auto_commit=True, auto_expunge=True)

    async def get_performance_stats(self, hours: int = 24) -> dict:
        """Get performance statistics."""
        since = datetime.now(UTC) - timedelta(hours=hours)

        result = await self.repository.session.execute(
            select(
                func.count(m.SearchMetrics.id).label("total_searches"),
                func.avg(m.SearchMetrics.search_time_ms).label("avg_search_time"),
                func.avg(m.SearchMetrics.embedding_time_ms).label("avg_embedding_time"),
                func.avg(m.SearchMetrics.oracle_time_ms).label("avg_oracle_time"),
                func.avg(m.SearchMetrics.similarity_score).label("avg_similarity"),
                func.max(m.SearchMetrics.search_time_ms).label("max_search_time"),
                func.min(m.SearchMetrics.search_time_ms).label("min_search_time"),
            ).where(m.SearchMetrics.created_at > since)
        )
        row = result.first()

        return {
            "total_searches": row.total_searches or 0,
            "avg_search_time_ms": round(row.avg_search_time or 0, 2),
            "avg_embedding_time_ms": round(row.avg_embedding_time or 0, 2),
            "avg_oracle_time_ms": round(row.avg_oracle_time or 0, 2),
            "avg_similarity_score": round(row.avg_similarity or 0, 3),
            "max_search_time_ms": row.max_search_time or 0,
            "min_search_time_ms": row.min_search_time or 0,
            "period_hours": hours,
        }

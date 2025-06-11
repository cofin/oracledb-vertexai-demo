"""Tests for Oracle services."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas import SearchMetricsCreate
from app.services.account import (
    ChatConversationService,
    ResponseCacheService,
    SearchMetricsService,
    UserSessionService,
)


class TestUserSessionService:
    """Test cases for UserSessionService."""

    @pytest.fixture
    def session_service(self) -> UserSessionService:
        """Create a UserSessionService instance."""
        service = UserSessionService(MagicMock(), MagicMock())  # type: ignore[misc]
        service.create = AsyncMock()  # type: ignore[method-assign]
        service.get_one_or_none = AsyncMock()  # type: ignore[method-assign]
        service.update = AsyncMock()  # type: ignore[method-assign]
        service.repository = MagicMock()  # type: ignore[misc]
        service.repository.session = AsyncMock()
        return service

    async def test_create_session(self, session_service: UserSessionService) -> None:
        """Test session creation."""
        mock_session = MagicMock(
            id=uuid.uuid4(),
            session_id="test-session-id",
            user_id="user123",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        session_service.create.return_value = mock_session  # type: ignore[attr-defined]

        await session_service.create_session("user123", ttl_hours=24)

        session_service.create.assert_called_once()  # type: ignore[attr-defined]
        create_args = session_service.create.call_args[0][0]  # type: ignore[attr-defined]
        assert create_args["user_id"] == "user123"
        assert "session_id" in create_args
        assert "expires_at" in create_args

    async def test_get_active_session_valid(self, session_service: UserSessionService) -> None:
        """Test getting an active session."""
        future_time = datetime.now(UTC) + timedelta(hours=1)
        mock_session = MagicMock(expires_at=future_time)
        session_service.get_one_or_none.return_value = mock_session  # type: ignore[attr-defined]

        result = await session_service.get_active_session("test-session")

        assert result == mock_session
        session_service.get_one_or_none.assert_called_once_with(session_id="test-session")  # type: ignore[attr-defined]

    async def test_get_active_session_expired(self, session_service: UserSessionService) -> None:
        """Test getting an expired session returns None."""
        past_time = datetime.now(UTC) - timedelta(hours=1)
        mock_session = MagicMock(expires_at=past_time)
        session_service.get_one_or_none.return_value = mock_session  # type: ignore[attr-defined]

        result = await session_service.get_active_session("test-session")

        assert result is None

    async def test_update_session_data(self, session_service: UserSessionService) -> None:
        """Test updating session data."""
        future_time = datetime.now(UTC) + timedelta(hours=1)
        mock_session = MagicMock(
            id=uuid.uuid4(),
            data={"existing": "data"},
            expires_at=future_time,
        )
        session_service.get_active_session = AsyncMock(return_value=mock_session)  # type: ignore[method-assign]

        await session_service.update_session_data("test-session", {"new": "data"})

        session_service.update.assert_called_once_with(  # type: ignore[attr-defined]
            mock_session.id,
            {"data": {"existing": "data", "new": "data"}},
        )


class TestChatConversationService:
    """Test cases for ChatConversationService."""

    @pytest.fixture
    def conversation_service(self) -> ChatConversationService:
        """Create a ChatConversationService instance."""
        service = ChatConversationService(MagicMock(), MagicMock())  # type: ignore[misc]
        service.create = AsyncMock()  # type: ignore[method-assign]
        service.repository = MagicMock()  # type: ignore[misc]
        service.repository.session = AsyncMock()
        return service

    async def test_add_message(self, conversation_service: ChatConversationService) -> None:
        """Test adding a message to conversation."""
        session_id = uuid.uuid4()
        mock_message = MagicMock()
        conversation_service.create.return_value = mock_message  # type: ignore[attr-defined]

        await conversation_service.add_message(
            session_id=session_id,
            user_id="user123",
            role="user",
            content="Tell me about coffee",
            message_metadata={"test": "metadata"},
        )

        conversation_service.create.assert_called_once_with({  # type: ignore[attr-defined]
            "session_id": session_id,
            "user_id": "user123",
            "role": "user",
            "content": "Tell me about coffee",
            "message_metadata": {"test": "metadata"},
        })

    async def test_get_conversation_history(self, conversation_service: ChatConversationService) -> None:
        """Test getting conversation history."""
        mock_messages = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        conversation_service.repository.session.execute.return_value = mock_result

        result = await conversation_service.get_conversation_history("user123", limit=10)

        assert result == mock_messages
        conversation_service.repository.session.execute.assert_called_once()


class TestResponseCacheService:
    """Test cases for ResponseCacheService."""

    @pytest.fixture
    def cache_service(self) -> ResponseCacheService:
        """Create a ResponseCacheService instance."""
        service = ResponseCacheService(MagicMock(), MagicMock())  # type: ignore[misc]
        service.get_one_or_none = AsyncMock()  # type: ignore[method-assign]
        service.create = AsyncMock()  # type: ignore[method-assign]
        service.update = AsyncMock()  # type: ignore[method-assign]
        return service

    def test_generate_cache_key(self, cache_service: ResponseCacheService) -> None:
        """Test cache key generation."""
        key1 = cache_service._generate_cache_key("test query", "user1")  # noqa: SLF001
        key2 = cache_service._generate_cache_key("test query", "user1")  # noqa: SLF001
        key3 = cache_service._generate_cache_key("different query", "user1")  # noqa: SLF001

        assert key1 == key2  # Same input should generate same key
        assert key1 != key3  # Different input should generate different key

    async def test_get_cached_response_hit(self, cache_service: ResponseCacheService) -> None:
        """Test getting a cached response."""
        future_time = datetime.now(UTC) + timedelta(minutes=5)
        mock_cached = MagicMock(
            expires_at=future_time,
            response={"content": "cached response"},
            hit_count=1,
        )
        cache_service.get_one_or_none.return_value = mock_cached  # type: ignore[attr-defined]

        result = await cache_service.get_cached_response("test query", "user1")

        assert result == {"content": "cached response"}
        cache_service.update.assert_called_once()  # type: ignore[attr-defined]

    async def test_get_cached_response_miss(self, cache_service: ResponseCacheService) -> None:
        """Test cache miss."""
        cache_service.get_one_or_none.return_value = None  # type: ignore[attr-defined]

        result = await cache_service.get_cached_response("test query", "user1")

        assert result is None

    async def test_cache_response_new(self, cache_service: ResponseCacheService) -> None:
        """Test caching a new response."""
        cache_service.get_one_or_none.return_value = None  # type: ignore[attr-defined]

        await cache_service.cache_response(
            "test query",
            {"content": "new response"},
            ttl_minutes=5,
            user_id="user1",
        )

        cache_service.create.assert_called_once()  # type: ignore[attr-defined]
        create_args = cache_service.create.call_args[0][0]  # type: ignore[attr-defined]
        assert create_args["query_text"] == "test query"
        assert create_args["response"] == {"content": "new response"}
        assert create_args["hit_count"] == 0

    async def test_cache_response_update(self, cache_service: ResponseCacheService) -> None:
        """Test updating an existing cache entry."""
        mock_existing = MagicMock(id=uuid.uuid4())
        cache_service.get_one_or_none.return_value = mock_existing  # type: ignore[attr-defined]

        await cache_service.cache_response(
            "test query",
            {"content": "updated response"},
            ttl_minutes=5,
            user_id="user1",
        )

        cache_service.update.assert_called_once_with(  # type: ignore[attr-defined]
            mock_existing.id,
            {
                "response": {"content": "updated response"},
                "expires_at": cache_service.update.call_args[0][1]["expires_at"],  # type: ignore[attr-defined]
                "query_text": "test query",
            },
        )


class TestSearchMetricsService:
    """Test cases for SearchMetricsService."""

    @pytest.fixture
    def metrics_service(self) -> SearchMetricsService:
        """Create a SearchMetricsService instance."""
        service = SearchMetricsService(MagicMock(), MagicMock())  # type: ignore[misc]
        service.create = AsyncMock()  # type: ignore[method-assign]
        service.repository = MagicMock()  # type: ignore[misc]
        service.repository.session = AsyncMock()
        return service

    async def test_record_search(self, metrics_service: SearchMetricsService) -> None:
        """Test recording search metrics."""
        metrics_data = SearchMetricsCreate(
            query_id="test-query-id",
            user_id="user123",
            search_time_ms=150.5,
            embedding_time_ms=25.3,
            oracle_time_ms=120.2,
            similarity_score=0.95,
            result_count=5,
        )

        await metrics_service.record_search(metrics_data)

        metrics_service.create.assert_called_once_with(metrics_data.__dict__)  # type: ignore[attr-defined]

    async def test_get_performance_stats(self, metrics_service: SearchMetricsService) -> None:
        """Test getting performance statistics."""
        mock_row = MagicMock(
            total_searches=100,
            avg_search_time=75.5,
            avg_embedding_time=20.3,
            avg_oracle_time=50.2,
            avg_similarity=0.85,
            max_search_time=200.0,
            min_search_time=10.0,
        )
        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        metrics_service.repository.session.execute.return_value = mock_result

        stats = await metrics_service.get_performance_stats(hours=24)

        assert stats["total_searches"] == 100
        assert stats["avg_search_time_ms"] == 75.5
        assert stats["avg_embedding_time_ms"] == 20.3
        assert stats["avg_oracle_time_ms"] == 50.2
        assert stats["avg_similarity_score"] == 0.85
        assert stats["max_search_time_ms"] == 200.0
        assert stats["min_search_time_ms"] == 10.0
        assert stats["period_hours"] == 24

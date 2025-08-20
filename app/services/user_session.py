from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.repositories.user_session import UserSessionRepository
    from app.schemas import UserSessionDTO


class UserSessionService:
    """Oracle session management using a repository."""

    def __init__(self, user_session_repository: UserSessionRepository) -> None:
        """Initialize with user session repository."""
        self.repository = user_session_repository

    async def create_session(self, user_id: str, ttl_hours: int = 24) -> UserSessionDTO:
        """Create new session with automatic expiry."""
        return await self.repository.create_session(user_id, ttl_hours)

    async def get_active_session(self, session_id: str) -> UserSessionDTO | None:
        """Get session if not expired."""
        from datetime import UTC, datetime
        session = await self.repository.get_by_session_id(session_id)
        if session and session.expires_at.replace(tzinfo=UTC) > datetime.now(UTC):
            return session
        return None

    async def update_session_data(self, session_id: str, data: dict) -> UserSessionDTO:
        """Update session data."""
        session = await self.get_active_session(session_id)
        if not session:
            msg = "Session not found or expired"
            raise ValueError(msg)
        updated_data = {**session.data, **data}
        return await self.repository.update_session_data(session_id, updated_data)

    async def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        return await self.repository.cleanup_expired()

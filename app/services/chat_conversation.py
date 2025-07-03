from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:

    from app.db.repositories.chat_conversation import ChatConversationRepository
    from app.schemas import ChatConversationDTO


class ChatConversationService:
    """Conversation history using a repository."""

    def __init__(self, chat_conversation_repository: ChatConversationRepository) -> None:
        """Initialize with chat conversation repository."""
        self.repository = chat_conversation_repository

    async def add_message(
        self,
        session_id: UUID | bytes,
        user_id: str,
        role: str,
        content: str,
        message_metadata: dict | None = None,
    ) -> ChatConversationDTO:
        """Add message to conversation."""
        session_id_str = session_id.hex if isinstance(session_id, UUID) else session_id.hex()
        return await self.repository.add_message(
            session_id_str, user_id, role, content, message_metadata
        )

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        session_id: UUID | bytes | None = None,
    ) -> list[ChatConversationDTO]:
        """Get recent conversation history."""
        session_id_str = session_id.hex if isinstance(session_id, UUID) else session_id.hex() if session_id else None
        return await self.repository.get_conversation_history(user_id, limit, session_id_str)

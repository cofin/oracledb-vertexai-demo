import uuid

import msgspec
import oracledb

from app.schemas import ChatConversationDTO

from .base import BaseRepository


class ChatConversationRepository(BaseRepository[ChatConversationDTO]):
    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        super().__init__(connection, ChatConversationDTO)

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[ChatConversationDTO]:
        if session_id:
            query = """
                SELECT id, session_id, user_id, role, content, message_metadata, created_at, updated_at
                FROM chat_conversation
                WHERE user_id = :user_id AND session_id = :session_id
                ORDER BY created_at DESC
                FETCH FIRST :limit ROWS ONLY
            """
            params = {"user_id": user_id, "session_id": session_id, "limit": limit}
        else:
            query = """
                SELECT id, session_id, user_id, role, content, message_metadata, created_at, updated_at
                FROM chat_conversation
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                FETCH FIRST :limit ROWS ONLY
            """
            params = {"user_id": user_id, "limit": limit}
        return await self.fetch_all(query, params)

    async def add_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        message_metadata: dict | None = None,
    ) -> None:
        message_id = uuid.uuid4()
        query = """
            INSERT INTO chat_conversation (id, session_id, user_id, role, content, message_metadata)
            VALUES (:id, :session_id, :user_id, :role, :content, :message_metadata)
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                {
                    "id": message_id.bytes,
                    "session_id": session_id,
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                    "message_metadata": msgspec.json.encode(message_metadata or {}).decode("utf-8"),
                },
            )
            await self.connection.commit()

    async def get_by_id(self, message_id: str) -> ChatConversationDTO | None:
        query = "SELECT id, session_id, user_id, role, content, message_metadata, created_at, updated_at FROM chat_conversation WHERE id = :id"
        return await self.fetch_one(query, {"id": message_id})

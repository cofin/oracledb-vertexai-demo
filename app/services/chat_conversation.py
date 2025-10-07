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

"""Chat conversation service using SQLSpec driver patterns."""


from typing import Any
from uuid import UUID

import msgspec

from app.services.base import SQLSpecService


class ChatConversationService(SQLSpecService):
    """Conversation history using SQLSpec driver patterns."""

    async def add_message(
        self,
        session_id: UUID | bytes,
        user_id: str,
        role: str,
        content: str,
        message_metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Add message to conversation."""
        # Handle session_id whether it's UUID or bytes from Oracle RAW
        session_id_value = session_id.bytes if isinstance(session_id, UUID) else session_id

        await self.driver.execute(
            """
            INSERT INTO chat_conversation (session_id, user_id, role, content, message_metadata)
            VALUES (:session_id, :user_id, :role, :content, :message_metadata)
            """,
            session_id=session_id_value,
            user_id=user_id,
            role=role,
            content=content,
            message_metadata=msgspec.json.encode(message_metadata or {}).decode("utf-8"),
        )

        # Get the inserted record
        row = await self.driver.select_one_or_none(
            """
            SELECT id, created_at, updated_at
            FROM chat_conversation
            WHERE session_id = :session_id AND user_id = :user_id
            ORDER BY created_at DESC
            FETCH FIRST 1 ROWS ONLY
            """,
            session_id=session_id_value,
            user_id=user_id,
        )

        if not row:
            msg = "Failed to create chat message"
            raise RuntimeError(msg)

        return {
            "id": row["id"],
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "message_metadata": message_metadata or {},
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        session_id: UUID | bytes | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent conversation history."""
        if session_id:
            # Handle session_id whether it's UUID or bytes from Oracle RAW
            session_id_value = session_id.bytes if isinstance(session_id, UUID) else session_id

            rows = await self.driver.select(
                """
                SELECT
                    id,
                    session_id,
                    user_id,
                    role,
                    content,
                    message_metadata,
                    created_at,
                    updated_at
                FROM chat_conversation
                WHERE user_id = :user_id AND session_id = :session_id
                ORDER BY created_at DESC
                FETCH FIRST :limit ROWS ONLY
                """,
                user_id=user_id,
                session_id=session_id_value,
                limit=limit,
            )
        else:
            rows = await self.driver.select(
                """
                SELECT
                    id,
                    session_id,
                    user_id,
                    role,
                    content,
                    message_metadata,
                    created_at,
                    updated_at
                FROM chat_conversation
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                FETCH FIRST :limit ROWS ONLY
                """,
                user_id=user_id,
                limit=limit,
            )

        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "role": row["role"],
                "content": row["content"],
                "message_metadata": row["message_metadata"]
                if isinstance(row["message_metadata"], dict)
                else msgspec.json.decode(row["message_metadata"])
                if row["message_metadata"]
                else {},
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

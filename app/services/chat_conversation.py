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

"""Chat conversation service using raw Oracle SQL."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import msgspec

from app.services.base import BaseService


class ChatConversationService(BaseService):
    """Conversation history using raw SQL."""

    async def add_message(
        self,
        session_id: UUID | bytes,
        user_id: str,
        role: str,
        content: str,
        message_metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Add message to conversation."""
        async with self.get_cursor() as cursor:
            # Handle session_id whether it's UUID or bytes from Oracle RAW
            session_id_value = session_id.bytes if isinstance(session_id, UUID) else session_id

            await cursor.execute(
                """
                INSERT INTO chat_conversation (session_id, user_id, role, content, message_metadata)
                VALUES (:session_id, :user_id, :role, :content, :message_metadata)
                """,
                {
                    "session_id": session_id_value,
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                    "message_metadata": msgspec.json.encode(message_metadata or {}).decode("utf-8"),
                },
            )

            await self.connection.commit()

            # Get the inserted record
            await cursor.execute(
                """
                SELECT id, created_at, updated_at
                FROM chat_conversation
                WHERE session_id = :session_id AND user_id = :user_id
                ORDER BY created_at DESC
                FETCH FIRST 1 ROWS ONLY
                """,
                {"session_id": session_id_value, "user_id": user_id},
            )

            row = await cursor.fetchone()
            if not row:
                msg = "Failed to create chat message"
                raise RuntimeError(msg)

            return {
                "id": row[0],
                "session_id": session_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "message_metadata": message_metadata or {},
                "created_at": row[1],
                "updated_at": row[2],
            }

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        session_id: UUID | bytes | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent conversation history."""
        async with self.get_cursor() as cursor:
            if session_id:
                # Handle session_id whether it's UUID or bytes from Oracle RAW
                session_id_value = session_id.bytes if isinstance(session_id, UUID) else session_id

                await cursor.execute(
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
                    {"user_id": user_id, "session_id": session_id_value, "limit": limit},
                )
            else:
                await cursor.execute(
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
                    {"user_id": user_id, "limit": limit},
                )

            return [
                {
                    "id": row[0],
                    "session_id": row[1],
                    "user_id": row[2],
                    "role": row[3],
                    "content": row[4],
                    "message_metadata": row[5]
                    if isinstance(row[5], dict)
                    else msgspec.json.decode(row[5])
                    if row[5]
                    else {},
                    "created_at": row[6],
                    "updated_at": row[7],
                }
                async for row in cursor
            ]

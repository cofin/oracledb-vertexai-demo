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

"""User session service using raw Oracle SQL."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import msgspec

from app.services.base import BaseService


class UserSessionService(BaseService):
    """Oracle session management using raw SQL."""

    async def create_session(self, user_id: str, ttl_hours: int = 24) -> dict[str, Any]:
        """Create new session with automatic expiry."""
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO user_session (session_id, user_id, data, expires_at)
                VALUES (:session_id, :user_id, :data, :expires_at)
                """,
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "data": "{}",  # Empty JSON object
                    "expires_at": expires_at,
                },
            )
            await self.connection.commit()

            # Return the created session
            session = await self.get_active_session(session_id)
            if not session:
                msg = "Failed to create session"
                raise RuntimeError(msg)
            return session

    async def get_active_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session if not expired."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT
                    id,
                    session_id,
                    user_id,
                    data,
                    expires_at,
                    created_at,
                    updated_at
                FROM user_session
                WHERE session_id = :session_id
                """,
                {"session_id": session_id},
            )

            row = await cursor.fetchone()
            if row:
                # Oracle TIMESTAMP WITH TIME ZONE might come back as naive datetime
                expires_at = row[4]
                if expires_at.tzinfo is None:
                    # Assume UTC if timezone is missing
                    expires_at = expires_at.replace(tzinfo=UTC)

                if expires_at > datetime.now(UTC):  # expires_at > now
                    return {
                        "id": row[0],
                        "session_id": row[1],
                        "user_id": row[2],
                        "data": row[3] if isinstance(row[3], dict) else msgspec.json.decode(row[3]) if row[3] else {},
                        "expires_at": expires_at,
                        "created_at": row[5],
                        "updated_at": row[6],
                    }
            return None

    async def update_session_data(self, session_id: str, data: dict) -> dict[str, Any]:
        """Update session data."""
        session = await self.get_active_session(session_id)
        if not session:
            msg = "Session not found or expired"
            raise ValueError(msg)

        # Merge with existing data
        updated_data = {**session["data"], **data}

        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                UPDATE user_session
                SET data = :data
                WHERE id = :id
                """,
                {
                    "id": session["id"],
                    "data": msgspec.json.encode(updated_data).decode("utf-8"),
                },
            )
            await self.connection.commit()

            result = await self.get_active_session(session_id)
            if not result:
                msg = "Failed to update session"
                raise RuntimeError(msg)
            return result

    async def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        now = datetime.now(UTC)
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                DELETE FROM user_session
                WHERE expires_at < :now
                """,
                {"now": now},
            )
            await self.connection.commit()
            return cursor.rowcount

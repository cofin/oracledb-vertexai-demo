import oracledb

from app.schemas import UserSessionDTO

from .base import BaseRepository


class UserSessionRepository(BaseRepository[UserSessionDTO]):
    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        super().__init__(connection, UserSessionDTO)

    async def get_by_session_id(self, session_id: str) -> UserSessionDTO | None:
        query = "SELECT id, session_id, user_id, data, expires_at, created_at, updated_at FROM user_session WHERE session_id = :session_id"
        return await self.fetch_one(query, {"session_id": session_id})

    async def create_session(self, user_id: str, ttl_hours: int = 24) -> UserSessionDTO:
        import uuid
        from datetime import UTC, datetime, timedelta
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        query = "INSERT INTO user_session (session_id, user_id, data, expires_at) VALUES (:session_id, :user_id, :data, :expires_at)"
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "data": "{}",
                    "expires_at": expires_at,
                },
            )
            await self.connection.commit()
        result = await self.get_by_session_id(session_id)
        if result is None:
            raise RuntimeError("Failed to create session")
        return result

    async def update_session_data(self, session_id: str, data: dict) -> UserSessionDTO:
        import msgspec
        query = "UPDATE user_session SET data = :data WHERE session_id = :session_id"
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                {
                    "session_id": session_id,
                    "data": msgspec.json.encode(data).decode("utf-8"),
                },
            )
            await self.connection.commit()
        result = await self.get_by_session_id(session_id)
        if result is None:
            raise RuntimeError("Failed to update session")
        return result

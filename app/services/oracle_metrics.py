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

"""Oracle-specific performance metrics service."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import oracledb


class OracleMetricsService:
    """Oracle-specific performance metrics."""

    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        """Initialize with Oracle connection."""
        self.connection = connection

    async def get_vector_index_stats(self) -> dict[str, Any]:
        """Get Oracle vector index statistics."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    i.index_name,
                    i.index_type,
                    i.status,
                    i.num_rows,
                    s.bytes / 1024 / 1024 as size_mb
                FROM user_indexes i
                LEFT JOIN user_segments s ON i.index_name = s.segment_name
                WHERE i.table_name = 'PRODUCT'
                AND i.index_type LIKE '%VECTOR%'
                """
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "index_name": row[0],
                    "index_type": row[1],
                    "status": row[2],
                    "vector_count": row[3],
                    "size_mb": round(row[4] or 0, 2),
                }
            return {}
        finally:
            cursor.close()

    async def get_inmemory_stats(self) -> dict[str, dict[str, Any]]:
        """Get Oracle In-Memory table statistics."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    table_name,
                    inmemory_size / 1024 / 1024 as size_mb,
                    populate_status,
                    inmemory_priority
                FROM v$im_segments
                WHERE owner = USER
                AND table_name IN ('INTENT_EXEMPLAR', 'RESPONSE_CACHE', 'PRODUCT')
                """
            )

            stats = {}
            async for row in cursor:
                stats[row[0]] = {
                    "size_mb": round(row[1] or 0, 2),
                    "status": row[2],
                    "priority": row[3],
                }
            return stats
        except Exception:  # noqa: BLE001
            # V$ views might not be accessible, return empty stats
            return {}
        finally:
            cursor.close()

    async def get_connection_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active_sessions,
                    SUM(CASE WHEN status = 'INACTIVE' THEN 1 ELSE 0 END) as inactive_sessions
                FROM v$session
                WHERE username = USER
                """
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "total_sessions": row[0] or 0,
                    "active_sessions": row[1] or 0,
                    "inactive_sessions": row[2] or 0,
                }
            return {"total_sessions": 0, "active_sessions": 0, "inactive_sessions": 0}
        except Exception:  # noqa: BLE001
            # V$ views might not be accessible
            return {"total_sessions": 0, "active_sessions": 0, "inactive_sessions": 0}
        finally:
            cursor.close()

    async def get_table_stats(self) -> dict[str, dict[str, Any]]:
        """Get table statistics for key tables."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    table_name,
                    num_rows,
                    avg_row_len,
                    blocks,
                    empty_blocks,
                    last_analyzed
                FROM user_tables
                WHERE table_name IN ('PRODUCT', 'RESPONSE_CACHE', 'SEARCH_METRICS', 'INTENT_EXEMPLAR')
                ORDER BY table_name
                """
            )

            stats = {}
            async for row in cursor:
                stats[row[0]] = {
                    "row_count": row[1] or 0,
                    "avg_row_length": row[2] or 0,
                    "blocks": row[3] or 0,
                    "empty_blocks": row[4] or 0,
                    "last_analyzed": row[5],
                }
            return stats
        finally:
            cursor.close()

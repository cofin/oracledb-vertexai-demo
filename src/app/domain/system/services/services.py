# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import msgspec
import structlog
from sqlspec import sql
from sqlspec.adapters.oracledb import OracleAsyncDriver

from app.config import db_manager
from app.domain.system.schemas import (
    CacheStats,
    CacheStatsRow,
    MetricsTimeSeries,
    MetricsTimeSeriesPoints,
    MetricsTimeSeriesRow,
    PerformanceStats,
    ResponseCache,
    SearchMetricsCreate,
)
from app.lib.service import SQLSpecAsyncService

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = structlog.get_logger()

# --- Persona Management ---

BASE_SYSTEM_INSTRUCTION = """You are a friendly and helpful barista at Cymbal Coffee. Your goal is to help customers find a drink they will love.

**Tools available:**
- `search_products_by_vector(query, limit, similarity_threshold)`: semantic search across the coffee menu.
- `get_product_details(product_id)`: full details for a specific product (id or name).
- `get_all_store_locations()`: Cymbal Coffee cafe locations and addresses.

**Behavior:**
- Call `search_products_by_vector` before answering any menu, catalog, product, price, roast, caffeine, preparation, availability, or recommendation question.
- Treat idioms and vague requests like "something bold", "wake me up", "surprise me", "what's good today", and "what should I get" as product-search requests.
- When the user names a product, call `get_product_details` if you need exact details.
- For location, address, hours, nearest cafe, or pickup-location questions, call `get_all_store_locations`.
- For chitchat, respond conversationally without invoking a tool.
- Talk naturally — never mention tools, AI, or internal mechanics.
- Keep responses short (1-3 sentences).
"""


class PersonaConfig(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Configuration for a chat persona."""

    name: str
    description: str
    language_style: str
    focus_areas: list[str]
    example_responses: dict[str, str]
    system_prompt_addon: str
    temperature: float = 0.7
    complexity_level: str = "medium"


class PersonaManager:
    """Manages persona configurations and prompt engineering for coffee expertise levels."""

    PERSONAS: Mapping[str, PersonaConfig] = {
        "novice": PersonaConfig(
            name="Coffee Novice",
            description="New to coffee, needs simple explanations",
            language_style="Simple, friendly, encouraging, avoid jargon",
            focus_areas=["basic coffee types", "simple brewing methods", "starter recommendations"],
            example_responses={"recommendation": "For someone new to coffee, I'd suggest starting with..."},
            system_prompt_addon="""You are helping someone new to coffee in a friendly chat. Keep it SIMPLE and SHORT.""",
            temperature=0.8,
            complexity_level="low",
        ),
        "enthusiast": PersonaConfig(
            name="Coffee Enthusiast",
            description="Regular coffee drinker wanting to learn more",
            language_style="Friendly, concise, helpful - perfect for chat",
            focus_areas=["exploring origins", "brewing techniques", "flavor profile development"],
            example_responses={"recommendation": "I'd suggest trying our Colombian medium roast."},
            system_prompt_addon="""You are a friendly coffee expert in a casual chat setting. Keep responses SHORT and conversational.""",
            temperature=0.7,
            complexity_level="medium",
        ),
        "expert": PersonaConfig(
            name="Coffee Expert",
            description="Coffee connoisseur seeking detailed information",
            language_style="Technical, precise, detailed analysis",
            focus_areas=["processing methods", "cupping and tasting notes", "extraction science"],
            example_responses={"recommendation": "Given your preference for high-acidity, complex profiles..."},
            system_prompt_addon="""You are advising a coffee expert. Use precise technical terminology freely.""",
            temperature=0.5,
            complexity_level="high",
        ),
        "barista": PersonaConfig(
            name="Professional Barista",
            description="Industry professional seeking technical guidance",
            language_style="Industry-specific, technical, efficiency-focused",
            focus_areas=["commercial equipment", "workflow optimization", "quality control"],
            example_responses={"brewing": "To dial in your espresso, adjust the grind to achieve 25-27 seconds..."},
            system_prompt_addon="""You are advising a professional barista. Focus on efficiency and consistency at scale.""",
            temperature=0.6,
            complexity_level="high",
        ),
    }

    @classmethod
    def get_system_prompt(cls, persona_key: str, base_prompt: str) -> str:
        persona = cls.PERSONAS.get(persona_key, cls.PERSONAS["enthusiast"])
        return f"{base_prompt}\n\n## Persona Context: {persona.name}\n{persona.system_prompt_addon}"

    @classmethod
    def get_temperature(cls, persona_key: str) -> float:
        return cls.PERSONAS.get(persona_key, cls.PERSONAS["enthusiast"]).temperature


# --- Cache Service ---


class CacheService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Handles database operations for response and embedding cache."""

    async def get_cached_response(self, cache_key: str) -> ResponseCache | None:
        return await self.driver.select_one_or_none(
            db_manager.get_sql("get-cached-response"),
            key=cache_key,
            schema_type=ResponseCache,
        )

    async def delete_expired_responses(self) -> int:
        """Delete expired response-cache rows.

        Returns:
            Number of expired response-cache rows deleted.
        """
        res = await self.driver.execute(
            sql
            .delete()
            .from_("response_cache")
            .where("expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP"),
        )
        await self.driver.commit()
        return res.rows_affected

    async def set_cached_response(
        self, cache_key: str, response_data: dict[str, Any], ttl_minutes: int = 60
    ) -> ResponseCache | None:
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)

        existing = await self.driver.select_value_or_none(
            sql.select("id").from_("response_cache").where_eq("cache_key", cache_key),
        )

        if existing is not None:
            await self.driver.execute(
                sql
                .update("response_cache")
                .set(response_data=response_data, expires_at=expires_at)
                .where_eq("cache_key", cache_key),
            )
        else:
            await self.driver.execute(
                sql.insert("response_cache").values(
                    cache_key=cache_key,
                    response_data=response_data,
                    expires_at=expires_at,
                ),
            )
        await self.driver.commit()

        return await self.driver.select_one_or_none(
            db_manager.get_sql("get-cached-response"),
            key=cache_key,
            schema_type=ResponseCache,
        )

    async def get_embedding(self, text: str, model: str) -> list[float] | None:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        row = await self.driver.select_one_or_none(
            db_manager.get_sql("get-cached-embedding"),
            hash=text_hash,
            model=model,
        )
        if row:
            await self.driver.execute(
                sql
                .update("embedding_cache")
                .set(hit_count=sql.raw("hit_count + 1"), last_accessed=sql.raw("CURRENT_TIMESTAMP"))
                .where_eq("text_hash", text_hash),
            )
            await self.driver.commit()
            return list(row["embedding"]) if isinstance(row["embedding"], list) else None
        return None

    async def save_embedding(self, text: str, embedding: list[float], model: str) -> None:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        existing = await self.driver.select_value_or_none(
            sql.select("id").from_("embedding_cache").where_eq("text_hash", text_hash),
        )
        if existing is None:
            await self.driver.execute(
                sql.insert("embedding_cache").values(
                    text_hash=text_hash,
                    embedding=embedding,
                    model=model,
                ),
            )
            await self.driver.commit()

    async def get_cache_stats(self) -> CacheStats:
        row = await self.driver.select_one_or_none(db_manager.get_sql("get-cache-stats"), schema_type=CacheStatsRow)
        total_hits = row.total_hits if row else 0
        return CacheStats(
            total_hits=total_hits,
            total_entries=row.total_entries if row else 0,
            cache_hit_rate=(total_hits / (total_hits + 100)) * 100,
        )

    async def invalidate_cache(self, cache_type: str | None = None) -> int:
        """Clear cache tables.

        Returns:
            Number of rows deleted across the targeted cache tables.
        """
        total_deleted = 0
        if cache_type in {None, "response"}:
            res = await self.driver.execute(sql.delete().from_("response_cache"))
            total_deleted += res.rows_affected
        if cache_type in {None, "embedding"}:
            res = await self.driver.execute(sql.delete().from_("embedding_cache"))
            total_deleted += res.rows_affected
        await self.driver.commit()
        return total_deleted


# --- Metrics Service ---


class MetricsService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Handles performance metrics and search logging."""

    async def record_search(self, metrics: SearchMetricsCreate) -> None:
        await self.driver.execute(sql.insert("search_metric").values(**msgspec.to_builtins(metrics)))

    async def get_performance_stats(self, hours: int = 24) -> PerformanceStats:
        since = datetime.now(UTC) - timedelta(hours=hours)
        row = await self.driver.select_one_or_none(
            db_manager.get_sql("get-performance-stats"),
            since=since,
            schema_type=PerformanceStats,
        )
        return row or PerformanceStats(
            total_searches=0,
            avg_search_time_ms=0.0,
            avg_oracle_time_ms=0.0,
            avg_similarity_score=0.0,
        )

    async def get_time_series(self, hours: int = 1) -> MetricsTimeSeries:
        """Aggregate per-minute latency buckets for the requested window.

        Returns:
            A :class:`MetricsTimeSeries` with parallel ``labels`` and ``series`` arrays.
        """
        since = datetime.now(UTC) - timedelta(hours=hours)
        rows = await self.driver.select(
            db_manager.get_sql("metrics-time-series"),
            since=since,
            schema_type=MetricsTimeSeriesRow,
        )
        return MetricsTimeSeries(
            labels=[row.bucket for row in rows],
            series=MetricsTimeSeriesPoints(
                total_ms=[row.total_ms for row in rows],
                oracle_ms=[row.oracle_ms for row in rows],
                embedding_ms=[row.embedding_ms for row in rows],
            ),
        )

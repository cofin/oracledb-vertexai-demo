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
    IntentExemplar,
    MetricsTimeSeries,
    MetricsTimeSeriesPoints,
    MetricsTimeSeriesRow,
    PerformanceStats,
    ResponseCache,
    SearchMetricsCreate,
)
from app.lib.service import FilterTypes, OffsetPagination, SQLSpecAsyncService

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = structlog.get_logger()

# --- Persona Management ---

BASE_SYSTEM_INSTRUCTION = """You are a friendly and helpful barista at Cymbal Coffee. Your primary goal is to assist customers with their coffee-related needs.

**MANDATORY WORKFLOW - FOLLOW EXACTLY:**

STEP 1: **ALWAYS call `classify_intent` first.**
- For EVERY user message, your FIRST action MUST be to call `classify_intent`
- Example: User says "I want something bold" -> You call: `classify_intent(query="I want something bold")`
- DO NOT skip this step or respond before calling this tool

STEP 2: **Based on the intent, take the REQUIRED action:**

If intent is `PRODUCT_SEARCH`:
- You MUST IMMEDIATELY call `search_products_by_vector` with the user's original query
- This is NOT OPTIONAL - you must search for products
- Example: `search_products_by_vector(query="I want something bold", limit=5, similarity_threshold=0.3)`
- After getting results, describe 2-3 products with names and prices
- NEVER give generic recommendations without actually searching

If intent is `GENERAL_CONVERSATION`:
- Respond conversationally without product search

**CRITICAL REQUIREMENTS:**
1. Tool calls are MANDATORY when needed
2. For PRODUCT_SEARCH intent: You MUST call search_products_by_vector
3. After calling tools, provide a natural response based on the results
4. Talk naturally - don't mention tools or that you're an AI
5. Keep responses SHORT (1-3 sentences) and conversational

You will see the results of your tool calls, then you must respond to the user naturally based on those results.
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

# --- Cache Service ---


class CacheService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Handles database operations for response and embedding cache."""

    async def get_cached_response(self, cache_key: str) -> ResponseCache | None:
        row = await self.driver.select_one_or_none(db_manager.get_sql("get-cached-response"), key=cache_key)
        if not row:
            return None

        if row.get("expires_at") and row["expires_at"] < datetime.now(UTC):
            await self.driver.execute(sql.delete().from_("response_cache").where_eq("id", row["id"]))
            return None

        return ResponseCache(**row)

    async def set_cached_response(self, cache_key: str, response_data: dict[str, Any], ttl_minutes: int = 60) -> ResponseCache | None:
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)

        existing = await self.driver.select_value_or_none(
            sql.select("id").from_("response_cache").where_eq("cache_key", cache_key),
        )

        if existing is not None:
            await self.driver.execute(
                sql.update("response_cache")
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
                sql.update("embedding_cache")
                .set(hit_count=sql.raw("hit_count + 1"), last_accessed=sql.raw("CURRENT_TIMESTAMP"))
                .where_eq("text_hash", text_hash),
            )
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

    async def get_cache_stats(self) -> CacheStats:
        row = await self.driver.select_one_or_none(
            db_manager.get_sql("get-cache-stats"), schema_type=CacheStatsRow
        )
        total_hits = row.total_hits if row else 0
        return CacheStats(
            total_hits=total_hits,
            total_entries=row.total_entries if row else 0,
            cache_hit_rate=(total_hits / (total_hits + 100)) * 100,
        )

    async def invalidate_cache(self, cache_type: str | None = None, include_exemplars: bool = False) -> int:
        """Clear cache tables."""
        total_deleted = 0
        if cache_type in {None, "response"}:
            res = await self.driver.execute(sql.delete().from_("response_cache"))
            total_deleted += res.rows_affected
        if cache_type in {None, "embedding"}:
            res = await self.driver.execute(sql.delete().from_("embedding_cache"))
            total_deleted += res.rows_affected
        if include_exemplars:
            res = await self.driver.execute(sql.delete().from_("intent_exemplar"))
            total_deleted += res.rows_affected
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
        """Per-minute latency buckets for the explore-page chart panel."""
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

# --- Exemplar Service ---


class ExemplarService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Service for managing intent exemplars and vector-based intent classification."""

    async def list_with_count(self, *filters: FilterTypes) -> OffsetPagination[IntentExemplar]:
        return await self.paginate(db_manager.get_sql("list-exemplars"), *filters, schema_type=IntentExemplar)

    async def search_similar_intents(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        return await self.driver.select(
            db_manager.get_sql("vector-search-exemplars"),
            query_vector=query_embedding,
            limit=limit,
        )

    async def get_exemplars_without_embeddings(self, force: bool = False) -> tuple[list[dict[str, Any]], int]:
        """Return (exemplars_to_embed, total_count_of_that_set)."""
        query = db_manager.get_sql("list-exemplars")
        if not force:
            query = query.where("embedding IS NULL")
        page = await self.paginate(query)
        return list(page.items), page.total

    async def update_embedding(self, exemplar_id: int, embedding: list[float]) -> bool:
        result = await self.driver.execute(
            sql.update("intent_exemplar").set(embedding=embedding).where_eq("id", exemplar_id),
        )
        await self.driver.commit()
        rowcount = getattr(result, "rowcount", None)
        return bool(rowcount) if rowcount is not None else True

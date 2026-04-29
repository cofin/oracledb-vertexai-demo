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

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import msgspec
import structlog
from sqlspec.adapters.oracledb import OracleAsyncDriver

from app.domain.system.schemas import ResponseCache, SearchMetricsCreate
from app.lib.service import SQLSpecAsyncService

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = structlog.get_logger()

# --- Persona Management ---

BASE_SYSTEM_INSTRUCTION = """You are a friendly and helpful barista at Cymbal Coffee. Your primary goal is to assist customers with their coffee-related needs.

**MANDATORY WORKFLOW - FOLLOW EXACTLY:**

STEP 1: **ALWAYS call `classify_intent` first.**
- For EVERY user message, your FIRST action MUST be to call `classify_intent`
- Example: User says "I want something bold" → You call: `classify_intent(query="I want something bold")`
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
        sql = "SELECT id, cache_key, response_data, created_at, expires_at FROM response_cache WHERE cache_key = :key"
        row = await self.driver.select_one_or_none(sql, {"key": cache_key})
        if not row:
            return None

        # Check expiration
        if row.get("expires_at") and row["expires_at"] < datetime.now(UTC):
            await self.driver.execute("DELETE FROM response_cache WHERE id = :id", {"id": row["id"]})
            return None

        return ResponseCache(**row)

    async def set_cached_response(self, cache_key: str, response_data: dict[str, Any], ttl_minutes: int = 60) -> ResponseCache | None:
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)

        # Check if exists
        check_sql = "SELECT id FROM response_cache WHERE cache_key = :key"
        existing = await self.driver.select_one_or_none(check_sql, {"key": cache_key})

        if existing:
            update_sql = "UPDATE response_cache SET response_data = :data, expires_at = :expires WHERE cache_key = :key"
            await self.driver.execute(update_sql, {"key": cache_key, "data": response_data, "expires": expires_at})
        else:
            insert_sql = "INSERT INTO response_cache (cache_key, response_data, expires_at) VALUES (:key, :data, :expires)"
            await self.driver.execute(insert_sql, {"key": cache_key, "data": response_data, "expires": expires_at})

        select_sql = "SELECT id, cache_key, response_data, created_at, expires_at FROM response_cache WHERE cache_key = :key"
        row = await self.driver.select_one_or_none(select_sql, {"key": cache_key})
        return ResponseCache(**row) if row else None

    async def get_embedding(self, text: str, model: str) -> list[float] | None:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        sql = "SELECT embedding FROM embedding_cache WHERE text_hash = :hash AND model = :model"
        row = await self.driver.select_one_or_none(sql, {"hash": text_hash, "model": model})
        if row:
            await self.driver.execute(
                "UPDATE embedding_cache SET hit_count = hit_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE text_hash = :hash",
                {"hash": text_hash},
            )
            return list(row["embedding"]) if isinstance(row["embedding"], list) else None
        return None

    async def save_embedding(self, text: str, embedding: list[float], model: str) -> None:
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        check_sql = "SELECT id FROM embedding_cache WHERE text_hash = :hash"
        existing = await self.driver.select_one_or_none(check_sql, {"hash": text_hash})

        if not existing:
            insert_sql = "INSERT INTO embedding_cache (text_hash, embedding, model) VALUES (:hash, :emb, :model)"
            await self.driver.execute(insert_sql, {"hash": text_hash, "emb": embedding, "model": model})

    async def get_cache_stats(self) -> dict[str, Any]:
        hit_sql = "SELECT SUM(hit_count) as total_hits, COUNT(*) as total_entries FROM embedding_cache"
        row = await self.driver.select_one_or_none(hit_sql)
        total_hits = row.get("total_hits", 0) if row else 0
        total_entries = row.get("total_entries", 0) if row else 0
        return {"total_hits": total_hits, "total_entries": total_entries, "cache_hit_rate": (total_hits / (total_hits + 100)) * 100}

    async def invalidate_cache(self, cache_type: str | None = None, include_exemplars: bool = False) -> int:
        """Clear cache tables."""
        total_deleted = 0
        if cache_type in {None, "response"}:
            sql = "DELETE FROM response_cache"
            res = await self.driver.execute(sql)
            total_deleted += res.rows_affected
        if cache_type in {None, "embedding"}:
            sql = "DELETE FROM embedding_cache"
            res = await self.driver.execute(sql)
            total_deleted += res.rows_affected
        if include_exemplars:
            sql = "DELETE FROM intent_exemplar"
            res = await self.driver.execute(sql)
            total_deleted += res.rows_affected
        return total_deleted

# --- Metrics Service ---

class MetricsService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Handles performance metrics and search logging."""

    async def record_search(self, metrics: SearchMetricsCreate) -> None:
        sql = """INSERT INTO search_metric (
            query_id, user_id, search_time_ms, embedding_time_ms, oracle_time_ms,
            ai_time_ms, intent_time_ms, similarity_score, result_count
        ) VALUES (
            :query_id, :user_id, :search_time_ms, :embedding_time_ms, :oracle_time_ms,
            :ai_time_ms, :intent_time_ms, :similarity_score, :result_count
        )"""
        await self.driver.execute(sql, msgspec.to_builtins(metrics))

    async def get_performance_stats(self, hours: int = 24) -> dict[str, Any]:
        sql = """SELECT COUNT(*) as total_searches, AVG(search_time_ms) as avg_search_time_ms,
                        AVG(oracle_time_ms) as avg_oracle_time_ms, AVG(similarity_score) as avg_similarity_score
                 FROM search_metric WHERE created_at > :since"""
        since = datetime.now(UTC) - timedelta(hours=hours)
        row = await self.driver.select_one_or_none(sql, {"since": since})
        return {k: v or 0 for k, v in row.items()} if row else {}

# --- Exemplar Service ---

class ExemplarService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Service for managing intent exemplars and vector-based intent classification."""

    async def search_similar_intents(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        sql = """SELECT intent, phrase, 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) as similarity, confidence_threshold
                 FROM intent_exemplar WHERE embedding IS NOT NULL
                 ORDER BY similarity DESC FETCH FIRST :limit ROWS ONLY"""
        return await self.driver.select(sql, {"query_vector": query_embedding, "limit": limit})

    async def get_exemplars_without_embeddings(self, force: bool = False) -> tuple[list[dict[str, Any]], int]:
        """Return (exemplars_needing_embedding, total_exemplar_count)."""
        clause = "" if force else "WHERE embedding IS NULL"
        rows = await self.driver.select(
            f"SELECT id, intent, phrase FROM intent_exemplar {clause} ORDER BY id",  # noqa: S608
        )
        total_row = await self.driver.select_one_or_none("SELECT COUNT(*) AS total FROM intent_exemplar")
        total = int(total_row["total"]) if total_row else len(rows)
        return rows, total

    async def update_embedding(self, exemplar_id: int, embedding: list[float]) -> bool:
        result = await self.driver.execute(
            "UPDATE intent_exemplar SET embedding = :embedding WHERE id = :id",
            {"embedding": embedding, "id": exemplar_id},
        )
        await self.driver.commit()
        rowcount = getattr(result, "rowcount", None)
        return bool(rowcount) if rowcount is not None else True

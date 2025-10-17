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

from datetime import datetime
from typing import Any
from uuid import UUID

import msgspec

from app.lib.schema import BaseStruct, CamelizedBaseStruct, Message, camel_case

__all__ = (
    "BaseStruct",
    "CamelizedBaseStruct",
    "ChartDataResponse",
    "ChatConversationCreate",
    "ChatConversationRead",
    "ChatMessage",
    "CoffeeChatMessage",
    "CoffeeChatReply",
    "EmbeddingCache",
    "HistoryMeta",
    "IntentResult",
    "Message",
    "MetricCard",
    "MetricsSummaryResponse",
    "ResponseCache",
    "SearchMetricsCreate",
    "SimilarIntent",
    "TimeSeriesData",
    "UserSessionCreate",
    "UserSessionRead",
    "VectorDemoRequest",
    "VectorDemoResult",
    "camel_case",
)


class SimilarIntent(msgspec.Struct, array_like=True, omit_defaults=True):
    """Represents a similar intent found by vector search."""

    intent: str
    phrase: str
    similarity: float
    confidence_threshold: float


class IntentResult(msgspec.Struct, array_like=True, omit_defaults=True):
    """Result of intent classification."""

    intent: str
    confidence: float
    exemplar_phrase: str
    embedding_cache_hit: bool
    fallback_used: bool


class CoffeeChatMessage(msgspec.Struct):
    """Chat message input DTO."""

    message: str
    persona: str = "enthusiast"


# Oracle-specific DTOs


class UserSessionCreate(msgspec.Struct, array_like=True, omit_defaults=True):
    """Session creation payload."""

    user_id: str
    data: dict = {}


class UserSessionRead(msgspec.Struct, array_like=True, omit_defaults=True):
    """Session response payload."""

    id: UUID
    session_id: str
    user_id: str
    data: dict
    expires_at: datetime
    created_at: datetime


class ChatConversationCreate(msgspec.Struct, array_like=True, omit_defaults=True):
    """Conversation creation payload."""

    session_id: UUID
    user_id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    message_metadata: dict = {}


class ChatConversationRead(msgspec.Struct, array_like=True, omit_defaults=True):
    """Conversation response payload."""

    id: UUID
    user_id: str
    role: str
    content: str
    message_metadata: dict
    created_at: datetime


class SearchMetricsCreate(msgspec.Struct, array_like=True, omit_defaults=True, kw_only=True):
    """Metrics creation payload."""

    query_id: str
    user_id: str | None = None
    search_time_ms: float
    embedding_time_ms: float
    oracle_time_ms: float
    ai_time_ms: float = 0.0
    intent_time_ms: float = 0.0
    similarity_score: float | None = None
    result_count: int


class ChatMessage(msgspec.Struct, array_like=True, omit_defaults=True):
    """Individual chat message."""

    message: str
    source: str  # 'human' | 'ai' | 'system'


class CoffeeChatReply(msgspec.Struct, array_like=True, omit_defaults=True):
    """Complete chat response."""

    message: str
    messages: list[ChatMessage]
    answer: str
    query_id: str
    search_metrics: dict = {}
    from_cache: bool = False
    embedding_cache_hit: bool = False
    intent_detected: str = "GENERAL_CONVERSATION"


# Legacy TypedDict for compatibility (to be removed)
class HistoryMeta(msgspec.Struct, array_like=True, omit_defaults=True):
    """History metadata."""

    conversation_id: str
    user_id: str


# Dashboard API DTOs


class MetricCard(msgspec.Struct, array_like=True, omit_defaults=True):
    """Metric card data for dashboard."""

    label: str
    value: str | float
    trend: str = "neutral"  # up, down, neutral
    trend_value: float | None = None


class MetricsSummaryResponse(msgspec.Struct, array_like=True, omit_defaults=True):
    """Metrics summary response."""

    total_searches: MetricCard
    avg_response_time: MetricCard
    avg_oracle_time: MetricCard
    cache_hit_rate: MetricCard


class TimeSeriesData(msgspec.Struct, omit_defaults=True):
    """Time series data for charts."""

    labels: list[str]
    total_latency: list[float]
    oracle_latency: list[float]
    vertex_latency: list[float]


class ChartDataResponse(msgspec.Struct, omit_defaults=True):
    """Chart data response."""

    time_series: TimeSeriesData
    scatter_data: list[dict[str, float]]
    breakdown_data: dict[str, Any]


class VectorDemoRequest(msgspec.Struct, omit_defaults=True):
    """Vector search demo request."""

    query: str


class VectorDemoResult(msgspec.Struct, array_like=True, omit_defaults=True):
    """Vector search demo result."""

    product_name: str
    description: str
    similarity_score: float
    search_time_ms: float


# Cache schemas


class ResponseCache(msgspec.Struct, omit_defaults=True):
    """Response cache entry."""

    id: int
    cache_key: str
    response_data: dict[str, Any]
    created_at: datetime
    expires_at: datetime | None = None


class EmbeddingCache(msgspec.Struct, omit_defaults=True):
    """Embedding cache entry."""

    id: int
    text_hash: str
    embedding: list[float]
    model: str
    created_at: datetime
    last_accessed: datetime
    hit_count: int = 0

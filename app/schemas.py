from __future__ import annotations

from typing import TYPE_CHECKING, Any, NewType

import msgspec

from app.lib.schema import BaseStruct, CamelizedBaseStruct, Message, camel_case

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

__all__ = (
    "BaseStruct",
    "CamelizedBaseStruct",
    "ChartDataResponse",
    "ChatConversationCreate",
    "ChatConversationRead",
    "ChatMessage",
    "CoffeeChatMessage",
    "CoffeeChatReply",
    "HistoryMeta",
    "Message",
    "MetricCard",
    "MetricsSummaryResponse",
    "SearchMetricsCreate",
    "TimeSeriesData",
    "UserSessionCreate",
    "UserSessionRead",
    "VectorDemoRequest",
    "VectorDemoResult",
    "camel_case",
)

ProductId = NewType("ProductId", int)
ShopId = NewType("ShopId", int)
CompanyId = NewType("CompanyId", int)
InventoryId = NewType("InventoryId", UUID)
SessionId = NewType("SessionId", str)
UserId = NewType("UserId", str)
QueryId = NewType("QueryId", str)


class CoffeeChatMessage(msgspec.Struct):
    """Chat message input DTO."""

    message: str = msgspec.field(min_length=1, max_length=2000)
    persona: str = "enthusiast"


# Oracle-specific DTOs


class UserSessionCreate(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Session creation payload."""

    user_id: UserId
    data: dict = {}


class UserSessionRead(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Session response payload."""

    id: UUID
    session_id: SessionId
    user_id: UserId
    data: dict
    expires_at: datetime
    created_at: datetime


class ChatConversationCreate(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Conversation creation payload."""

    session_id: UUID
    user_id: UserId
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    message_metadata: dict = {}


class ChatConversationRead(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Conversation response payload."""

    id: UUID
    user_id: UserId
    role: str
    content: str
    message_metadata: dict
    created_at: datetime


class SearchMetricsCreate(msgspec.Struct, gc=False, array_like=True, omit_defaults=True, kw_only=True):
    """Metrics creation payload."""

    query_id: QueryId
    user_id: UserId | None = None
    search_time_ms: float
    embedding_time_ms: float
    oracle_time_ms: float
    ai_time_ms: float = 0.0
    intent_time_ms: float = 0.0
    similarity_score: float | None = None
    result_count: int


class ChatMessage(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Individual chat message."""

    message: str
    source: str  # 'human' | 'ai' | 'system'


class CoffeeChatReply(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Complete chat response."""

    message: str
    messages: list[ChatMessage]
    answer: str
    query_id: QueryId
    session_id: SessionId
    search_metrics: dict = {}
    from_cache: bool = False
    embedding_cache_hit: bool = False
    intent_detected: str = "GENERAL_CONVERSATION"


# Legacy TypedDict for compatibility (to be removed)
class HistoryMeta(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """History metadata."""

    conversation_id: str
    user_id: UserId


# Dashboard API DTOs


class MetricCard(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Metric card data for dashboard."""

    label: str
    value: str | float
    trend: str = "neutral"  # up, down, neutral
    trend_value: float | None = None


class MetricsSummaryResponse(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Metrics summary response."""

    total_searches: MetricCard
    avg_response_time: MetricCard
    avg_oracle_time: MetricCard
    cache_hit_rate: MetricCard


class TimeSeriesData(msgspec.Struct, gc=False, omit_defaults=True):
    """Time series data for charts."""

    labels: list[str]
    total_latency: list[float]
    oracle_latency: list[float]
    vertex_latency: list[float]


class ChartDataResponse(msgspec.Struct, gc=False, omit_defaults=True):
    """Chart data response."""

    time_series: TimeSeriesData
    scatter_data: list[dict[str, float]]
    breakdown_data: dict[str, Any]


class VectorDemoRequest(msgspec.Struct, gc=False, omit_defaults=True):
    """Vector search demo request."""

    query: str


class VectorDemoResult(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Vector search demo result."""

    product_name: str
    description: str
    similarity_score: float
    search_time_ms: float


class CompanyDTO(BaseStruct, gc=False, array_like=True, omit_defaults=True):
    """Company DTO."""

    id: CompanyId
    name: str
    created_at: datetime
    updated_at: datetime


class ShopDTO(BaseStruct, gc=False, array_like=True, omit_defaults=True):
    """Shop DTO."""

    id: ShopId
    name: str
    address: str
    created_at: datetime
    updated_at: datetime


class ProductDTO(BaseStruct, gc=False, array_like=True, omit_defaults=True):
    """Product DTO."""

    id: ProductId
    name: str
    description: str
    price: float


class IntentExemplarDTO(BaseStruct, gc=False, array_like=True, omit_defaults=True):
    """Intent Exemplar DTO."""

    id: int
    intent: str
    phrase: str
    embedding: list[float] | None
    created_at: datetime
    updated_at: datetime


class UserSessionDTO(BaseStruct, gc=False, array_like=True, omit_defaults=True):
    """User Session DTO."""

    id: UUID
    session_id: SessionId
    user_id: UserId
    data: dict
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


class ChatConversationDTO(BaseStruct, gc=False, array_like=True, omit_defaults=True):
    """Chat Conversation DTO."""

    id: UUID
    session_id: UUID
    user_id: UserId
    role: str
    content: str
    message_metadata: dict
    created_at: datetime
    updated_at: datetime


class ResponseCacheDTO(BaseStruct, gc=False, array_like=True, omit_defaults=True):
    """Response Cache DTO."""

    id: UUID
    cache_key: str
    query_text: str
    response: dict
    expires_at: datetime
    hit_count: int
    created_at: datetime
    updated_at: datetime


class SearchMetricsDTO(BaseStruct, gc=False, array_like=True, omit_defaults=True):
    """Search Metrics DTO."""

    id: UUID
    query_id: QueryId
    user_id: UserId | None
    search_time_ms: float
    embedding_time_ms: float
    oracle_time_ms: float
    ai_time_ms: float
    intent_time_ms: float
    similarity_score: float | None
    result_count: int
    created_at: datetime
    updated_at: datetime


class InventoryDTO(BaseStruct, gc=False, array_like=True, omit_defaults=True):
    """Inventory DTO."""

    id: InventoryId
    shop_id: ShopId
    shop_name: str
    shop_address: str
    product_id: ProductId
    product_name: str
    current_price: float
    description: str
    company_name: str
    created_at: datetime
    updated_at: datetime

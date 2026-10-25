# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""APEX-safe JSON contracts for product-domain REST Source Catalog endpoints."""

from datetime import datetime
from typing import Annotated, Literal

from msgspec import Meta, field

from app.domain.products.schemas._products import ProductAvailability, StockStatus, Store
from app.lib.schema import CamelizedFrozenStruct

__all__ = (
    "ApexInventoryList",
    "ApexInventorySummaryList",
    "ApexInventorySummaryRow",
    "ApexOpenAPIStatus",
    "ApexProduct",
    "ApexProductList",
    "ApexRecommendation",
    "ApexRecommendationRequest",
    "ApexRecommendationResponse",
    "ApexStoreList",
    "ApexVectorReadiness",
    "ApexVectorStatus",
    "NonEmptyQuery",
    "PositiveLimit",
    "RecommendationMode",
)

RecommendationMode = Literal["hybrid", "vector", "fallback"]

PositiveLimit = Annotated[int, Meta(ge=1, le=100)]
NonEmptyQuery = Annotated[str, Meta(min_length=1, max_length=500)]


class ApexProduct(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=True):
    """Product catalog row safe for APEX REST Source Catalogs."""

    id: int
    name: str
    description: str
    price: float
    category: str | None = None
    sku: str | None = None
    in_stock: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ApexProductList(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Paginated product rows for APEX catalog consumption."""

    items: list[ApexProduct]
    total: int
    limit: int
    offset: int


class ApexStoreList(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Seeded store rows safe for APEX display."""

    items: list[Store]
    total: int


class ApexInventorySummaryRow(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Inventory aggregate counts for a single store."""

    store_id: int
    store_name: str
    product_count: int
    in_stock_count: int
    low_stock_count: int
    out_of_stock_count: int
    total_quantity: int


class ApexInventorySummaryList(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Inventory summary collection."""

    items: list[ApexInventorySummaryRow]
    total: int


class ApexInventoryList(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Inventory or availability row collection."""

    items: list[ProductAvailability]
    total: int


class ApexRecommendationRequest(
    CamelizedFrozenStruct, frozen=True, forbid_unknown_fields=True, kw_only=True, omit_defaults=False
):
    """Recommendation request body accepted by APEX REST clients."""

    query: NonEmptyQuery
    store_id: int | None = None
    limit: PositiveLimit = 5


class ApexRecommendation(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=True):
    """Grounded recommendation row returned to APEX."""

    product_id: int
    name: str
    description: str
    price: float
    category: str | None = None
    sku: str | None = None
    similarity_score: float | None = None
    store_id: int | None = None
    store_name: str | None = None
    quantity_available: int | None = None
    stock_status: StockStatus | None = None
    pickup_available: bool | None = None


class ApexRecommendationResponse(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=True):
    """Recommendation response with vector timings when available."""

    query: str
    mode: RecommendationMode
    items: list[ApexRecommendation]
    total: int
    cache_hit: bool | None = None
    embedding_time_ms: float | None = None
    oracle_time_ms: float | None = None
    fallback_reason: str | None = None


class ApexVectorReadiness(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Oracle vector and hybrid RRF index readiness counts."""

    product_count: int = 0
    embedded_product_count: int = 0
    hybrid_index_count: int | None = None


class ApexVectorStatus(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Embedding provider and Oracle vector/hybrid readiness status."""

    embedding_model: str
    embedding_dimensions: int
    provider_configured: bool
    oracle_vector_ready: bool
    hybrid_rrf_ready: bool
    product_count: int
    embedded_product_count: int


class ApexOpenAPIStatus(CamelizedFrozenStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Catalog metadata for APEX display."""

    title: str
    api_version: str
    base_path: str
    tags: list[str] = field(default_factory=list)
    operation_ids: list[str] = field(default_factory=list)

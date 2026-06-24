# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""APEX-safe JSON contracts for product-domain REST Source Catalog endpoints."""

from datetime import datetime
from typing import Annotated, Literal

from msgspec import Meta, field

from app.domain.products.schemas._products import ProductAvailability, StockStatus, Store
from app.lib.schema import CamelizedBaseStruct

RecommendationMode = Literal["vector", "fallback"]

PositiveLimit = Annotated[int, Meta(ge=1, le=100)]
NonEmptyQuery = Annotated[str, Meta(min_length=1, max_length=500)]


class ApexProduct(CamelizedBaseStruct, kw_only=True, omit_defaults=True):
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


class ApexProductList(CamelizedBaseStruct, kw_only=True):
    """Paginated product rows for APEX catalog consumption."""

    items: list[ApexProduct]
    total: int
    limit: int
    offset: int


class ApexStoreList(CamelizedBaseStruct, kw_only=True):
    """Seeded store rows safe for APEX display."""

    items: list[Store]
    total: int


class ApexInventorySummaryRow(CamelizedBaseStruct, kw_only=True):
    """Inventory aggregate counts for a single store."""

    store_id: int
    store_name: str
    product_count: int
    in_stock_count: int
    low_stock_count: int
    out_of_stock_count: int
    total_quantity: int


class ApexInventorySummaryList(CamelizedBaseStruct, kw_only=True):
    """Inventory summary collection."""

    items: list[ApexInventorySummaryRow]
    total: int


class ApexInventoryList(CamelizedBaseStruct, kw_only=True):
    """Inventory or availability row collection."""

    items: list[ProductAvailability]
    total: int


class ApexRecommendationRequest(CamelizedBaseStruct, forbid_unknown_fields=True, kw_only=True):
    """Recommendation request body accepted by APEX REST clients."""

    query: NonEmptyQuery
    store_id: int | None = None
    limit: PositiveLimit = 5


class ApexRecommendation(CamelizedBaseStruct, kw_only=True, omit_defaults=True):
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


class ApexRecommendationResponse(CamelizedBaseStruct, kw_only=True, omit_defaults=True):
    """Recommendation response with vector timings when available."""

    query: str
    mode: RecommendationMode
    items: list[ApexRecommendation]
    total: int
    cache_hit: bool | None = None
    embedding_time_ms: float | None = None
    oracle_time_ms: float | None = None
    fallback_reason: str | None = None


class ApexVectorReadiness(CamelizedBaseStruct, kw_only=True):
    """Oracle vector data readiness counts."""

    product_count: int = 0
    embedded_product_count: int = 0


class ApexVectorStatus(CamelizedBaseStruct, kw_only=True):
    """Embedding provider and Oracle vector readiness status."""

    embedding_model: str
    embedding_dimensions: int
    provider_configured: bool
    oracle_vector_ready: bool
    product_count: int
    embedded_product_count: int


class ApexOpenAPIStatus(CamelizedBaseStruct, kw_only=True):
    """Catalog metadata for APEX display."""

    title: str
    api_version: str
    base_path: str
    tags: list[str] = field(default_factory=list)
    operation_ids: list[str] = field(default_factory=list)

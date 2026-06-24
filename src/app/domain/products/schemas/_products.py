# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — used in handler-visible schema; Litestar OpenAPI needs runtime ref
from typing import Any, Literal

from msgspec import field

from app.lib.schema import CamelizedBaseStruct

StockStatus = Literal["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"]


class Product(CamelizedBaseStruct, omit_defaults=True):
    """Product entity from database."""

    id: int
    name: str
    price: float
    description: str
    category: str | None = None
    sku: str | None = None
    in_stock: bool = True
    metadata: dict[str, Any] | None = None
    embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Store(CamelizedBaseStruct, omit_defaults=True):
    """Store location entity from database."""

    id: int
    name: str
    address: str
    created_at: datetime
    updated_at: datetime
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    phone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    google_place_id: str | None = None
    hours: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class StoreHours(CamelizedBaseStruct, omit_defaults=True):
    """Store hours response contract."""

    store_id: int
    store_name: str
    timezone: str | None = None
    hours: dict[str, Any] = field(default_factory=dict)


class StoreDistance(Store, omit_defaults=True):
    """Store row plus local coordinate ranking score."""

    distance_miles: float = 0.0
    distance_score: float | None = None


class StoreProductInventory(CamelizedBaseStruct, omit_defaults=True):
    """Store-product inventory row."""

    id: int
    store_id: int
    product_id: int
    quantity_available: int
    stock_status: StockStatus
    pickup_available: bool = True
    updated_at: datetime | None = None


class ProductAvailability(StoreProductInventory, omit_defaults=True):
    """Product availability row with store and product display fields."""

    store_name: str = ""
    store_address: str = ""
    store_city: str | None = None
    store_state: str | None = None
    store_zip: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    google_place_id: str | None = None
    product_name: str = ""
    product_description: str = ""
    product_category: str | None = None
    product_sku: str | None = None
    product_price: float | None = None
    distance_miles: float | None = None


class VectorQuery(CamelizedBaseStruct, omit_defaults=True):
    """A user-supplied vector-search query string."""

    query: str


class ProductMatch(CamelizedBaseStruct, omit_defaults=True):
    """A product row returned by vector similarity search.

    Slim projection of `product` (no embedding, no metadata) plus the
    `similarity_score` derived in SQL via `1 - VECTOR_DISTANCE(...)`.
    """

    id: int
    name: str
    description: str
    price: float
    similarity_score: float
    store_id: int | None = None
    store_name: str | None = None
    quantity_available: int | None = None
    stock_status: StockStatus | None = None
    pickup_available: bool | None = None


class VectorDemoMatch(CamelizedBaseStruct, omit_defaults=True):
    """A vector-search hit shaped for the explore-page Panel 1 partial."""

    name: str
    description: str
    price: float
    similarity: float


class VectorDemo(CamelizedBaseStruct, omit_defaults=True):
    """Full ``POST /api/vector-demo`` payload for SPA / JSON consumers."""

    results: list[VectorDemoMatch]
    search_time_ms: float
    embedding_time_ms: float
    oracle_time_ms: float
    cache_hit: bool
    performance_level: str
    debug_timings: dict[str, float]


class ExplainPlanRow(CamelizedBaseStruct, omit_defaults=True):
    """A structured operation row parsed from Oracle ``DBMS_XPLAN`` text."""

    id: str
    operation: str
    name: str = ""
    rows: str = ""
    bytes: str = ""
    cost: str = ""
    time: str = ""
    raw_line: str = ""
    is_vector: bool = False


class ExplainPlan(CamelizedBaseStruct, omit_defaults=True):
    """Oracle EXPLAIN PLAN output for the vector-search SQL (Panel 2)."""

    plan_lines: list[str]
    plan_summary: str
    plan_rows: list[ExplainPlanRow] = field(default_factory=list)

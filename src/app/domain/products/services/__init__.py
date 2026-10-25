# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Products domain services package."""

from __future__ import annotations

from app.domain.products.services._embedding import (
    EMBEDDING_PURPOSE_INSTRUCTIONS,
    GEMINI_EMBEDDING_2_MODEL,
    BatchProgressCallback,
    VertexAIService,
)
from app.domain.products.services._maps import build_store_directions_url, build_store_search_url
from app.domain.products.services._products import ProductService
from app.domain.products.services._stores import StoreService
from app.domain.products.services._vector import (
    RRF_DEFAULT_K,
    SERVICE_UNAVAILABLE_MESSAGE,
    OracleVectorSearchService,
    build_explore_sql_phases,
    build_explore_telemetry_context,
    build_vector_demo_matches,
    unavailable_plan,
)

__all__ = (
    "EMBEDDING_PURPOSE_INSTRUCTIONS",
    "GEMINI_EMBEDDING_2_MODEL",
    "RRF_DEFAULT_K",
    "SERVICE_UNAVAILABLE_MESSAGE",
    "BatchProgressCallback",
    "OracleVectorSearchService",
    "ProductService",
    "StoreService",
    "VertexAIService",
    "build_explore_sql_phases",
    "build_explore_telemetry_context",
    "build_store_directions_url",
    "build_store_search_url",
    "build_vector_demo_matches",
    "unavailable_plan",
)

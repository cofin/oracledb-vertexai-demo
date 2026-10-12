# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Products domain services package."""

from __future__ import annotations

from app.domain.products.services._embedding import (
    EMBEDDING_PURPOSE_INSTRUCTIONS,
    GEMINI_EMBEDDING_2_MODEL,
    EmbeddingService,
    OracleVectorSearchService,
    VertexAIService,
)
from app.domain.products.services._inventory import InventoryService
from app.domain.products.services._maps import MapsService, build_store_directions_url, build_store_search_url
from app.domain.products.services._products import ProductService
from app.domain.products.services._stores import StoreService

__all__ = (
    "EMBEDDING_PURPOSE_INSTRUCTIONS",
    "GEMINI_EMBEDDING_2_MODEL",
    "EmbeddingService",
    "InventoryService",
    "MapsService",
    "OracleVectorSearchService",
    "ProductService",
    "StoreService",
    "VertexAIService",
    "build_store_directions_url",
    "build_store_search_url",
)

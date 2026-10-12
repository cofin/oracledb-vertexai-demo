# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Hybrid RRF search and route resolution schemas for the chat domain."""

from __future__ import annotations

from typing import Literal

import msgspec

__all__ = (
    "HybridProductCandidate",
    "HybridRouteLabel",
    "HybridSearchRow",
    "HybridStoreCandidate",
    "HybridTurnContext",
    "TermHitRow",
)

HybridRouteLabel = Literal[
    "PRODUCT_RAG",
    "PRODUCT_AVAILABILITY",
    "STORE_LOCATION",
    "ORDER_STATUS",
    "GENERAL_CONVERSATION",
]


class HybridSearchRow(msgspec.Struct, kw_only=True):
    """Single row projected by ``hybrid-search-turn`` across route, product, and store CTEs."""

    entity_type: str
    entity_id: int
    route_label: str | None = None
    name: str = ""
    description: str | None = None
    category: str | None = None
    price: float | None = None
    in_stock: int | bool | None = None
    city: str | None = None
    state: str | None = None
    address: str | None = None
    lexical_score: float = 0.0
    vector_similarity: float | None = None
    lexical_rank: int | None = None
    vector_rank: int | None = None
    rrf_score: float = 0.0


class TermHitRow(msgspec.Struct, kw_only=True):
    """Per-term Oracle Text lexical hit count returned by ``hybrid-term-hits``."""

    term: str
    hit_count: int = 0


class HybridProductCandidate(msgspec.Struct, kw_only=True):
    """Fused product candidate with lexical, vector, and RRF rank metadata."""

    id: int
    name: str
    description: str
    category: str | None = None
    price: float = 0.0
    in_stock: bool = True
    lexical_score: float = 0.0
    vector_similarity: float = 0.0
    lexical_rank: int | None = None
    vector_rank: int | None = None
    rrf_score: float = 0.0


class HybridStoreCandidate(msgspec.Struct, kw_only=True):
    """Fused store candidate matched by Oracle Text multi-column search."""

    id: int
    name: str
    address: str
    city: str | None = None
    state: str | None = None
    lexical_score: float = 0.0
    lexical_rank: int | None = None
    rrf_score: float = 0.0


class HybridTurnContext(msgspec.Struct, kw_only=True):
    """Complete single-query hybrid retrieval and routing context for one chat turn."""

    user_message: str
    oracle_text_query: str | None
    intent_detected: HybridRouteLabel
    is_deterministic: bool
    route_confidence: float
    route_scores: dict[str, float] = msgspec.field(default_factory=dict)
    products: list[HybridProductCandidate] = msgspec.field(default_factory=list)
    stores: list[HybridStoreCandidate] = msgspec.field(default_factory=list)
    term_hits: dict[str, int] = msgspec.field(default_factory=dict)
    off_menu_terms: list[str] = msgspec.field(default_factory=list)
    oracle_time_ms: float = 0.0

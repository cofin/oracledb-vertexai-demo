# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat domain service package."""

from ._grounded import GroundedRouteService, GroundedTurnResult
from ._router import HybridRouteResolver, build_oracle_text_query, extract_candidate_terms
from ._telemetry import (
    SearchMetrics,
    SQLPhase,
    build_hybrid_sql_phases,
    build_map_actions,
    build_response_cache_phase,
    build_search_metrics,
    build_sql_phase,
    extract_location_filters,
    extract_product_query,
    request_coordinates,
    safe_location_context,
    summarize_vector,
)

__all__ = (
    "GroundedRouteService",
    "GroundedTurnResult",
    "HybridRouteResolver",
    "SQLPhase",
    "SearchMetrics",
    "build_hybrid_sql_phases",
    "build_map_actions",
    "build_oracle_text_query",
    "build_response_cache_phase",
    "build_search_metrics",
    "build_sql_phase",
    "extract_candidate_terms",
    "extract_location_filters",
    "extract_product_query",
    "request_coordinates",
    "safe_location_context",
    "summarize_vector",
)

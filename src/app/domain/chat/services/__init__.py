# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat domain service package."""

from ._composers import (
    ORDER_STATUS_ANSWER,
    build_candidate_block,
    compose_availability_answer,
    compose_grounded_selection,
    compose_off_menu_alternative,
    compose_product_rag_answer,
    compose_store_location_answer,
    partition_availability_rows,
    select_grounded_products,
)
from ._grounded import GroundedRouteService, GroundedTurnResult
from ._router import HybridRouteResolver, extract_candidate_terms
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
    "ORDER_STATUS_ANSWER",
    "GroundedRouteService",
    "GroundedTurnResult",
    "HybridRouteResolver",
    "SQLPhase",
    "SearchMetrics",
    "build_candidate_block",
    "build_hybrid_sql_phases",
    "build_map_actions",
    "build_response_cache_phase",
    "build_search_metrics",
    "build_sql_phase",
    "compose_availability_answer",
    "compose_grounded_selection",
    "compose_off_menu_alternative",
    "compose_product_rag_answer",
    "compose_store_location_answer",
    "extract_candidate_terms",
    "extract_location_filters",
    "extract_product_query",
    "partition_availability_rows",
    "request_coordinates",
    "safe_location_context",
    "select_grounded_products",
    "summarize_vector",
)

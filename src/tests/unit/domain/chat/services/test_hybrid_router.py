# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Behavioral unit tests for Oracle 26ai single-query Hybrid RRF routing and query sanitization."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import msgspec
import pytest

from app.domain.chat.schemas import HybridSearchRow, HybridTurnContext, TermHitRow
from app.domain.chat.services import _router as router_module
from app.domain.chat.services._router import HybridRouteResolver, build_oracle_text_query, extract_candidate_terms
from app.lib.schema import FrozenBaseStruct
from app.lib.service import OracleLoaderService
from app.lib.text_search import (
    ORACLE_TEXT_RESERVED_WORDS,
    ORACLE_TEXT_STOPWORDS,
    build_oracle_proximity_query,
    extract_search_tokens,
)
from tests.support.paths import APP_ROOT, TESTS_ROOT

HYBRID_SQL = APP_ROOT / "db" / "sql" / "hybrid.sql"
GOLDEN_JSONL = TESTS_ROOT / "fixtures" / "routing_golden.jsonl"


def _load_golden_cases() -> list[dict[str, Any]]:
    lines = [line.strip() for line in Path(GOLDEN_JSONL).read_text(encoding="utf-8").splitlines() if line.strip()]
    return [msgspec.json.decode(line.encode("utf-8")) for line in lines]


def test_hybrid_sql_defines_turn_term_hits_and_product_queries() -> None:
    """Verify hybrid.sql exists and defines hybrid-search-turn, hybrid-term-hits, and hybrid-search-products."""
    assert HYBRID_SQL.exists(), "src/app/db/sql/hybrid.sql must exist"
    text = HYBRID_SQL.read_text(encoding="utf-8")
    assert "-- name: hybrid-search-turn" in text
    assert "-- name: hybrid-term-hits" in text
    assert "-- name: hybrid-search-products" in text
    assert "CONTAINS(" in text
    assert "VECTOR_DISTANCE(" in text
    assert "FETCH APPROX FIRST" in text
    assert "JSON_TABLE(" in text


def test_build_oracle_text_query_escapes_punctuation_and_reserved_words() -> None:
    """Verify build_oracle_text_query wraps searchable tokens in braces and strips operators/stopwords."""
    sanitized = build_oracle_text_query("NOT AND OR {decaf} espresso-roast? ~*() %")
    assert sanitized is not None
    assert "{decaf}" in sanitized
    assert "{espresso-roast}" in sanitized
    assert "{not}" not in sanitized.lower()
    assert "{and}" not in sanitized.lower()
    assert "{or}" not in sanitized.lower()
    assert "ACCUM" in sanitized

    assert build_oracle_text_query("   ??? ... !!! ") is None
    assert build_oracle_text_query("the a an and or not") is None


def test_extract_candidate_terms_identifies_brand_and_proper_noun_tokens() -> None:
    """Verify extract_candidate_terms captures off-menu brand names like Folgers and Starbucks."""
    terms_folgers = extract_candidate_terms("Do you carry Folgers dark roast?")
    assert "Folgers" in terms_folgers

    terms_starbucks = extract_candidate_terms("Can I buy Starbucks Pike Place here?")
    assert "Starbucks" in terms_starbucks
    assert "Pike" in terms_starbucks


@pytest.mark.anyio
@pytest.mark.parametrize("case", _load_golden_cases(), ids=lambda c: f"golden_{c['id']:02d}")
async def test_hybrid_route_resolver_passes_golden_suite(case: dict[str, Any]) -> None:
    """Verify HybridRouteResolver resolves all 30 golden prompts into expected routes and determinism flags."""
    mock_driver = AsyncMock()
    rows: list[HybridSearchRow] = [
        HybridSearchRow(
            entity_type="route",
            entity_id=1,
            route_label=case["top_route"],
            name=case["top_route"],
            description="Top exemplar",
            category=None,
            price=None,
            in_stock=None,
            city=None,
            state=None,
            address=None,
            lexical_score=80.0,
            vector_similarity=0.88,
            lexical_rank=1,
            vector_rank=1,
            rrf_score=float(case["top_rrf"]),
        ),
        HybridSearchRow(
            entity_type="route",
            entity_id=2,
            route_label=case["second_route"],
            name=case["second_route"],
            description="Second exemplar",
            category=None,
            price=None,
            in_stock=None,
            city=None,
            state=None,
            address=None,
            lexical_score=35.0,
            vector_similarity=0.62,
            lexical_rank=2,
            vector_rank=2,
            rrf_score=float(case["second_rrf"]),
        ),
    ]

    if "product_lexical_score" in case or "product_vector_sim" in case:
        rows.append(
            HybridSearchRow(
                entity_type="product",
                entity_id=101,
                route_label=None,
                name="Ethiopian Yirgacheffe",
                description="Floral citrus pour-over light roast",
                category="coffee_beans",
                price=19.5,
                in_stock=1,
                city=None,
                state=None,
                address=None,
                lexical_score=float(case.get("product_lexical_score", 0.0)),
                vector_similarity=float(case.get("product_vector_sim", 0.0)),
                lexical_rank=1,
                vector_rank=1,
                rrf_score=0.032,
            )
        )

    if "store_lexical_score" in case:
        rows.append(
            HybridSearchRow(
                entity_type="store",
                entity_id=201,
                route_label=None,
                name="Bishop Arts",
                description="408 N Bishop Ave",
                category=None,
                price=None,
                in_stock=None,
                city="Dallas",
                state="TX",
                address="408 N Bishop Ave, Dallas, TX 75208",
                lexical_score=float(case["store_lexical_score"]),
                vector_similarity=None,
                lexical_rank=1,
                vector_rank=None,
                rrf_score=0.0164,
            )
        )

    term_hits_map: dict[str, int] = case.get("term_hits", {})
    term_hit_rows = [TermHitRow(term=k, hit_count=v) for k, v in term_hits_map.items()]

    async def fake_select(statement: Any, **kwargs: Any) -> list[Any]:
        schema_type = kwargs.get("schema_type")
        if schema_type is TermHitRow:
            return term_hit_rows
        return rows

    mock_driver.select = AsyncMock(side_effect=fake_select)

    resolver = HybridRouteResolver(mock_driver)
    turn_ctx = await resolver.resolve_turn(user_message=case["prompt"], query_embedding=[0.01] * 3072)

    assert isinstance(turn_ctx, HybridTurnContext)
    assert turn_ctx.intent_detected == case["expected_intent"]
    assert turn_ctx.is_deterministic is bool(case["expected_deterministic"])
    expected_off_menu = case.get("expected_off_menu_terms", [])
    for off_term in expected_off_menu:
        assert off_term in turn_ctx.off_menu_terms


def test_text_search_proximity_and_token_extraction() -> None:
    """Verify shared Oracle Text token extraction and NEAR proximity query construction."""
    assert "near" in ORACLE_TEXT_RESERVED_WORDS
    assert "accum" in ORACLE_TEXT_RESERVED_WORDS
    assert "the" in ORACLE_TEXT_STOPWORDS
    assert extract_search_tokens("What fruity OR floral light-roast coffees?") == [
        "fruity",
        "floral",
        "light-roast",
        "coffees",
    ]
    assert build_oracle_proximity_query("light roast") == (
        "NEAR(({light}, {roast}), 6, TRUE) ACCUM ({light} ACCUM {roast})"
    )
    assert build_oracle_proximity_query("light roast", max_span=4, in_order=False) == (
        "NEAR(({light}, {roast}), 4, FALSE) ACCUM ({light} ACCUM {roast})"
    )
    assert build_oracle_proximity_query("espresso") == "{espresso}"
    assert build_oracle_proximity_query("the and or not") is None


def test_hybrid_route_resolver_uses_oracle_loader_service_and_frozen_schemas() -> None:
    """Verify HybridRouteResolver inherits from OracleLoaderService with frozen schemas and zero app.config imports."""
    assert issubclass(HybridRouteResolver, OracleLoaderService)
    assert issubclass(HybridSearchRow, FrozenBaseStruct)
    assert issubclass(TermHitRow, FrozenBaseStruct)
    assert issubclass(HybridTurnContext, FrozenBaseStruct)
    assert "app.config" not in inspect.getsource(router_module)

    terms_dfw = extract_candidate_terms("Do you have espresso in Plano or Fort Worth or Arlington or Frisco or Irving?")
    assert terms_dfw == []

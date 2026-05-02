# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Vector-search response-shape integration test against a real Oracle container.

Exercises the ``vector-search-products`` named query and asserts the
``ProductMatch`` contract: ``price`` is populated, ``similarity_score`` is in
``[0, 1]``, and no synthetic ``distance`` field is exposed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.domain.products.schemas import ProductMatch

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlspec.adapters.oracledb import OracleAsyncDriver

    from app.domain.products.services import ProductService

pytestmark = pytest.mark.anyio


# A non-degenerate, deterministic 3072-dim FLOAT32 vector. Equal-magnitude
# values mean cosine distance is well-defined; using 0.5 (rather than all-zeros)
# avoids the all-zero norm edge case that Oracle's VECTOR_DISTANCE rejects.
def _seed_embedding() -> list[float]:
    return [0.5] * 3072


async def _seed_product_with_embedding(driver: OracleAsyncDriver, sku: str) -> int:
    """Insert a uniquely keyed embedded product. Returns its id."""
    embedding = _seed_embedding()
    await driver.execute(
        """
        INSERT INTO product (name, description, price, category, sku, in_stock, embedding)
        VALUES (:name, :description, :price, :category, :sku, TRUE, :embedding)
        """,
        name=f"Vector Test Product {sku}",
        description="Deterministic product for vector-search integration tests",
        price=9.99,
        category="Coffee",
        sku=sku,
        embedding=embedding,
    )
    await driver.commit()
    result = await driver.select_one_or_none("SELECT id FROM product WHERE sku = :sku", sku=sku)
    assert result is not None
    return int(result["id"])


async def test_vector_search_returns_typed_product_matches_with_price(
    driver: OracleAsyncDriver,
    product_service: ProductService,
    unique_test_id: str,
    tracked_product_skus: Callable[[str], None],
) -> None:
    """search_by_vector must return ProductMatch instances with price>0 and similarity_score in [0,1]."""
    sku = f"VECTOR-{unique_test_id}"
    tracked_product_skus(sku)
    seed_id = await _seed_product_with_embedding(driver, sku)

    matches = await product_service.search_by_vector(
        query_embedding=_seed_embedding(),
        similarity_threshold=0.5,
        limit=5,
    )

    assert matches, "vector search must return at least the seed product when querying with its own embedding"

    for match in matches:
        assert isinstance(match, ProductMatch), (
            f"search_by_vector must return ProductMatch instances, got {type(match).__name__}"
        )
        assert match.price > 0, (
            f"ProductMatch.price must be populated and >0 (got {match.price!r}); "
            "guards against the current_price/price column-name regression"
        )
        # Cosine similarity of FP32-stored vectors against an FP64 query can land
        # a few ULPs above 1.0 for self-matches. Allow a small numerical fuzz.
        assert -1e-6 <= match.similarity_score <= 1 + 1e-6, (
            f"similarity_score must be in [0, 1] (±1e-6), got {match.similarity_score!r}"
        )
        assert not hasattr(match, "current_price"), (
            "ProductMatch must not expose 'current_price' — the column was renamed to 'price'"
        )
        assert not hasattr(match, "distance"), (
            "ProductMatch must not expose 'distance' — the band-aid mapping has been removed"
        )

    seed_match = next((m for m in matches if m.id == seed_id), None)
    assert seed_match is not None, "the seed product must appear in its own self-match query"
    # Querying with the same embedding should yield the highest possible similarity (≈1.0).
    assert seed_match.similarity_score == pytest.approx(1.0, abs=1e-3), (
        f"self-query should yield similarity_score≈1.0, got {seed_match.similarity_score}"
    )


async def test_vector_search_named_query_runs_via_db_manager(
    driver: OracleAsyncDriver,
    unique_test_id: str,
    tracked_product_skus: Callable[[str], None],
) -> None:
    """Exercise the named query end-to-end and confirm the column shape Oracle returns."""
    sku = f"VECTOR-SQL-{unique_test_id}"
    tracked_product_skus(sku)
    await _seed_product_with_embedding(driver, sku)

    from app.config import db_manager

    rows = await driver.select(
        db_manager.get_sql("vector-search-products"),
        query_vector=_seed_embedding(),
        threshold=0.5,
        limit=5,
    )

    assert rows, "vector-search-products must return rows when an embedded product matches"
    expected_keys = {"id", "name", "description", "price", "similarity_score"}
    actual_keys = set(rows[0].keys())
    assert expected_keys <= actual_keys, (
        f"vector-search-products projection mismatch: expected {expected_keys}, got {actual_keys}"
    )
    assert "current_price" not in actual_keys, (
        "vector-search-products must not project 'current_price' — the column was renamed to 'price'"
    )

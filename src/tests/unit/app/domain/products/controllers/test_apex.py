# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""APEX-safe product-domain JSON API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.products.controllers import ApexController
from app.domain.products.schemas import (
    ApexInventorySummaryRow,
    ApexProduct,
    ApexRecommendationRequest,
    ApexVectorReadiness,
    ProductAvailability,
    ProductMatch,
    Store,
)

pytestmark = pytest.mark.anyio


def _product(product_id: int = 1, name: str = "Cold Brew Nitro") -> ApexProduct:
    return ApexProduct(
        id=product_id,
        name=name,
        description="A velvety cold coffee with a creamy finish.",
        price=5.25,
        category="Cold Coffee",
        sku=f"COFFEE-{product_id}",
        in_stock=True,
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        updated_at=datetime(2026, 6, 23, tzinfo=UTC),
    )


def _store(store_id: int = 16) -> Store:
    return Store(
        id=store_id,
        name="Cymbal Coffee Dallas Arts District",
        address="1717 N Harwood St",
        city="Dallas",
        state="TX",
        zip="75201",
        latitude=32.7876,
        longitude=-96.7994,
        timezone="America/Chicago",
        google_place_id="ChIJ-safe-demo",
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        updated_at=datetime(2026, 6, 23, tzinfo=UTC),
    )


def _availability(product_id: int = 1, store_id: int = 16) -> ProductAvailability:
    return ProductAvailability(
        id=101,
        store_id=store_id,
        product_id=product_id,
        quantity_available=8,
        stock_status="IN_STOCK",
        pickup_available=True,
        updated_at=datetime(2026, 6, 23, tzinfo=UTC),
        store_name="Cymbal Coffee Dallas Arts District",
        store_address="1717 N Harwood St",
        store_city="Dallas",
        store_state="TX",
        store_zip="75201",
        latitude=32.7876,
        longitude=-96.7994,
        google_place_id="ChIJ-safe-demo",
        product_name="Cold Brew Nitro",
        product_description="A velvety cold coffee with a creamy finish.",
        product_category="Cold Coffee",
        product_sku="COFFEE-1",
        product_price=5.25,
    )


async def test_apex_products_apply_catalog_filters() -> None:
    products_service = MagicMock()
    products_service.list_apex_products = AsyncMock(return_value=([_product()], 1))

    response = await ApexController.list_products.fn(
        ApexController(owner=MagicMock()),
        products_service=products_service,
        q="nitro",
        category="Cold Coffee",
        limit=10,
        offset=5,
    )

    products_service.list_apex_products.assert_awaited_once_with(
        q="nitro",
        category="Cold Coffee",
        limit=10,
        offset=5,
    )
    assert response.total == 1
    assert response.limit == 10
    assert response.offset == 5
    assert response.items[0].name == "Cold Brew Nitro"


def test_apex_product_contract_omits_internal_metadata_and_embedding() -> None:
    """APEX catalog products do not advertise internal vector or metadata fields."""
    assert "metadata" not in ApexProduct.__annotations__
    assert "embedding" not in ApexProduct.__annotations__


async def test_apex_inventory_and_availability_are_json_data() -> None:
    stores_service = MagicMock()
    stores_service.get_all_stores = AsyncMock(return_value=[_store()])
    stores_service.list_inventory_summary = AsyncMock(
        return_value=[
            ApexInventorySummaryRow(
                store_id=16,
                store_name="Cymbal Coffee Dallas Arts District",
                product_count=3,
                in_stock_count=2,
                low_stock_count=1,
                out_of_stock_count=0,
                total_quantity=23,
            )
        ]
    )
    stores_service.list_store_inventory = AsyncMock(return_value=[_availability()])
    stores_service.find_stores_with_product = AsyncMock(return_value=[_availability()])
    controller = ApexController(owner=MagicMock())

    stores = await ApexController.list_stores.fn(controller, stores_service=stores_service)
    summary = await ApexController.inventory_summary.fn(controller, stores_service=stores_service)
    inventory = await ApexController.store_inventory.fn(controller, stores_service=stores_service, store_id=16)
    availability = await ApexController.product_availability.fn(
        controller,
        stores_service=stores_service,
        product_id=1,
    )

    assert stores.items[0].google_place_id == "ChIJ-safe-demo"
    assert summary.items[0].in_stock_count == 2
    assert inventory.items[0].product_name == "Cold Brew Nitro"
    assert availability.items[0].store_name == "Cymbal Coffee Dallas Arts District"


async def test_apex_recommendations_use_store_aware_vector_search() -> None:
    vector_search_service = MagicMock()
    vector_search_service.similarity_search = AsyncMock(
        return_value=(
            [
                ProductMatch(
                    id=1,
                    name="Cold Brew Nitro",
                    description="A velvety cold coffee with a creamy finish.",
                    price=5.25,
                    similarity_score=0.91,
                    store_id=16,
                    store_name="Cymbal Coffee Dallas Arts District",
                    quantity_available=8,
                    stock_status="IN_STOCK",
                    pickup_available=True,
                )
            ],
            False,
            {"embedding_ms": 4.0, "oracle_ms": 2.0},
        )
    )
    products_service = MagicMock()
    products_service.list_apex_products = AsyncMock()
    stores_service = MagicMock()

    response = await ApexController.recommendations.fn(
        ApexController(owner=MagicMock()),
        vector_search_service=vector_search_service,
        products_service=products_service,
        stores_service=stores_service,
        data=ApexRecommendationRequest(query="nitro cold brew", store_id=16, limit=3),
    )

    vector_search_service.similarity_search.assert_awaited_once_with(
        "nitro cold brew",
        k=3,
        threshold=0.5,
        store_id=16,
    )
    products_service.list_apex_products.assert_not_awaited()
    assert response.mode == "vector"
    assert response.cache_hit is False
    assert response.items[0].similarity_score == pytest.approx(0.91)
    assert response.items[0].store_id == 16


async def test_apex_recommendations_fall_back_to_catalog_search_when_vector_unavailable() -> None:
    vector_search_service = MagicMock()
    vector_search_service.similarity_search = AsyncMock(side_effect=RuntimeError("credentials unavailable"))
    products_service = MagicMock()
    products_service.list_apex_products = AsyncMock(return_value=([_product()], 1))
    stores_service = MagicMock()

    response = await ApexController.recommendations.fn(
        ApexController(owner=MagicMock()),
        vector_search_service=vector_search_service,
        products_service=products_service,
        stores_service=stores_service,
        data=ApexRecommendationRequest(query="nitro", limit=2),
    )

    products_service.list_apex_products.assert_awaited_once_with(q="nitro", category=None, limit=2, offset=0)
    assert response.mode == "fallback"
    assert response.items[0].product_id == 1
    assert response.items[0].similarity_score is None


async def test_apex_recommendations_fall_back_to_store_inventory_when_store_scoped() -> None:
    vector_search_service = MagicMock()
    vector_search_service.similarity_search = AsyncMock(side_effect=RuntimeError("credentials unavailable"))
    products_service = MagicMock()
    products_service.list_apex_products = AsyncMock()
    stores_service = MagicMock()
    stores_service.search_store_inventory = AsyncMock(return_value=[_availability()])

    response = await ApexController.recommendations.fn(
        ApexController(owner=MagicMock()),
        vector_search_service=vector_search_service,
        products_service=products_service,
        stores_service=stores_service,
        data=ApexRecommendationRequest(query="nitro", store_id=16, limit=2),
    )

    stores_service.search_store_inventory.assert_awaited_once_with(store_id=16, q="nitro", limit=2)
    products_service.list_apex_products.assert_not_awaited()
    assert response.mode == "fallback"
    assert response.items[0].product_id == 1
    assert response.items[0].store_id == 16
    assert response.items[0].quantity_available == 8


async def test_apex_recommendations_reraises_unexpected_vector_errors() -> None:
    vector_search_service = MagicMock()
    vector_search_service.similarity_search = AsyncMock(side_effect=ValueError("bad vector shape"))
    products_service = MagicMock()
    products_service.list_apex_products = AsyncMock()
    stores_service = MagicMock()

    with pytest.raises(ValueError, match="bad vector shape"):
        await ApexController.recommendations.fn(
            ApexController(owner=MagicMock()),
            vector_search_service=vector_search_service,
            products_service=products_service,
            stores_service=stores_service,
            data=ApexRecommendationRequest(query="nitro", limit=2),
        )

    products_service.list_apex_products.assert_not_awaited()


async def test_apex_status_endpoints_report_catalog_and_vector_readiness() -> None:
    products_service = MagicMock()
    products_service.get_vector_readiness = AsyncMock(
        return_value=ApexVectorReadiness(product_count=4, embedded_product_count=3)
    )
    vertex_ai_service = MagicMock(embedding_model="gemini-embedding-2", embedding_dimensions=3072)
    vector_search_service = MagicMock(vertex_ai_service=vertex_ai_service)
    controller = ApexController(owner=MagicMock())

    vector_status = await ApexController.vector_status.fn(
        controller,
        products_service=products_service,
        vector_search_service=vector_search_service,
    )
    catalog_status = await ApexController.openapi_status.fn(controller)

    assert vector_status.embedding_model == "gemini-embedding-2"
    assert vector_status.embedding_dimensions == 3072
    assert vector_status.oracle_vector_ready is True
    assert isinstance(vector_status.provider_configured, bool)
    assert catalog_status.base_path == "/api/apex"
    assert "ApexListProducts" in catalog_status.operation_ids


async def test_apex_service_helpers_use_named_sql_and_typed_rows(mock_driver) -> None:
    from app.domain.products.services import ProductService, StoreService

    mock_driver.select = AsyncMock(return_value=[_product()])
    mock_driver.select_value = AsyncMock(return_value=1)
    products = await ProductService(mock_driver).list_apex_products(
        q="nitro",
        category="Cold Coffee",
        limit=10,
        offset=5,
    )

    rows, total = products
    assert total == 1
    assert rows[0].name == "Cold Brew Nitro"
    select_call = mock_driver.select.await_args
    assert select_call is not None
    assert select_call.kwargs["schema_type"] is ApexProduct
    assert select_call.kwargs["q"] == "nitro"

    mock_driver.select = AsyncMock(
        return_value=[
            ApexInventorySummaryRow(
                store_id=16,
                store_name="Cymbal Coffee Dallas Arts District",
                product_count=3,
                in_stock_count=2,
                low_stock_count=1,
                out_of_stock_count=0,
                total_quantity=23,
            )
        ]
    )
    summary = await StoreService(mock_driver).list_inventory_summary()

    assert summary[0].store_id == 16
    summary_select_call = mock_driver.select.await_args
    assert summary_select_call is not None
    assert summary_select_call.kwargs["schema_type"] is ApexInventorySummaryRow


async def test_store_service_search_store_inventory_uses_named_sql(mock_driver) -> None:
    from app.domain.products.services import StoreService

    mock_driver.select = AsyncMock(return_value=[_availability()])

    results = await StoreService(mock_driver).search_store_inventory(store_id=16, q="nitro", limit=3)

    assert results[0].store_id == 16
    select_call = mock_driver.select.await_args
    assert select_call is not None
    assert "store_product_inventory" in str(select_call.args[0].sql)
    assert select_call.kwargs["store_id"] == 16
    assert select_call.kwargs["q"] == "nitro"
    assert select_call.kwargs["limit"] == 3
    assert select_call.kwargs["schema_type"] is ProductAvailability

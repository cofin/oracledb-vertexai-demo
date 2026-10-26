# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""APEX-safe JSON product-domain API."""

from litestar import get, post
from litestar.exceptions import ValidationException
from litestar.params import FromPath, FromQuery
from litestar_security import PublicController

from app.__metadata__ import __version__
from app.domain.products.schemas import (
    ApexInventoryList,
    ApexInventorySummaryList,
    ApexOpenAPIStatus,
    ApexProductList,
    ApexRecommendationRequest,
    ApexRecommendationResponse,
    ApexStoreList,
    ApexVectorStatus,
)
from app.domain.products.services import OracleVectorSearchService, ProductService, StoreService
from app.lib.di import Inject

__all__ = ("ApexController",)

_APEX_TAG = "APEX REST Catalog"
_OPERATION_IDS = [
    "ApexListProducts",
    "ApexListStores",
    "ApexInventorySummary",
    "ApexStoreInventory",
    "ApexProductAvailability",
    "ApexCreateRecommendations",
    "ApexVectorStatus",
    "ApexOpenAPIStatus",
]


class ApexController(PublicController):
    """JSON endpoints shaped for APEX REST Source Catalog consumption."""

    path = "/api/apex"
    tags = [_APEX_TAG]

    @get("/products", operation_id="ApexListProducts", name="apex:products", summary="APEX Product Catalog")
    async def list_products(
        self,
        products_service: Inject[ProductService],
        q: FromQuery[str | None] = None,
        category: FromQuery[str | None] = None,
        limit: FromQuery[int] = 50,
        offset: FromQuery[int] = 0,
    ) -> ApexProductList:
        """Return product catalog rows with APEX-safe filters."""
        limit = _bounded_limit(limit, default=50)
        offset = _bounded_offset(offset)
        items, total = await products_service.list_apex_products(
            q=_blank_to_none(q), category=_blank_to_none(category), limit=limit, offset=offset
        )
        return ApexProductList(items=items, total=total, limit=limit, offset=offset)

    @get("/stores", operation_id="ApexListStores", name="apex:stores", summary="APEX Store Catalog")
    async def list_stores(self, stores_service: Inject[StoreService]) -> ApexStoreList:
        """Return seeded demo stores with safe map coordinates and place IDs."""
        items = await stores_service.get_all_stores()
        return ApexStoreList(items=items, total=len(items))

    @get(
        "/inventory/summary",
        operation_id="ApexInventorySummary",
        name="apex:inventory_summary",
        summary="APEX Inventory Summary",
    )
    async def inventory_summary(self, stores_service: Inject[StoreService]) -> ApexInventorySummaryList:
        """Return inventory counts by store and stock status."""
        items = await stores_service.list_inventory_summary()
        return ApexInventorySummaryList(items=items, total=len(items))

    @get(
        "/stores/{store_id:int}/inventory",
        operation_id="ApexStoreInventory",
        name="apex:store_inventory",
        summary="APEX Store Inventory",
    )
    async def store_inventory(self, stores_service: Inject[StoreService], store_id: FromPath[int]) -> ApexInventoryList:
        """Return inventory rows for one store."""
        items = await stores_service.list_store_inventory(store_id)
        return ApexInventoryList(items=items, total=len(items))

    @get(
        "/products/{product_id:int}/availability",
        operation_id="ApexProductAvailability",
        name="apex:product_availability",
        summary="APEX Product Availability",
    )
    async def product_availability(
        self, stores_service: Inject[StoreService], product_id: FromPath[int]
    ) -> ApexInventoryList:
        """Return availability across stores for one product."""
        items = await stores_service.find_stores_with_product(product_id)
        return ApexInventoryList(items=items, total=len(items))

    @post(
        "/recommendations",
        operation_id="ApexCreateRecommendations",
        name="apex:recommendations",
        summary="APEX Product Recommendations",
    )
    async def recommendations(
        self, vector_search_service: Inject[OracleVectorSearchService], data: ApexRecommendationRequest
    ) -> ApexRecommendationResponse:
        """Return vector or hybrid recommendations, falling back to deterministic catalog search."""
        query = data.query.strip()
        if not query:
            raise ValidationException(detail="Query cannot be empty")
        limit = _bounded_limit(data.limit, default=5, maximum=25)
        return await vector_search_service.recommend_for_apex(query=query, limit=limit, store_id=data.store_id)

    @get("/vector/status", operation_id="ApexVectorStatus", name="apex:vector_status", summary="APEX Vector Status")
    async def vector_status(self, vector_search_service: Inject[OracleVectorSearchService]) -> ApexVectorStatus:
        """Return embedding/provider and Oracle vector readiness status."""
        return await vector_search_service.get_apex_vector_status()

    @get("/openapi/status", operation_id="ApexOpenAPIStatus", name="apex:openapi_status", summary="APEX OpenAPI Status")
    async def openapi_status(self) -> ApexOpenAPIStatus:
        """Return APEX catalog metadata and operation IDs."""
        return ApexOpenAPIStatus(
            title="Cymbal Coffee APEX REST API",
            api_version=__version__,
            base_path=self.path,
            tags=[_APEX_TAG],
            operation_ids=list(_OPERATION_IDS),
        )


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _bounded_limit(limit: int, *, default: int, maximum: int = 100) -> int:
    if limit < 1:
        return default
    return min(limit, maximum)


def _bounded_offset(offset: int) -> int:
    return max(offset, 0)

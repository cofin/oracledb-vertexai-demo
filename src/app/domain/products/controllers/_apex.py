# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""APEX-safe JSON product-domain API."""

import structlog
from litestar import Controller, get, post
from litestar.exceptions import ValidationException
from litestar.params import FromPath, FromQuery

from app.__metadata__ import __version__
from app.domain.products.controllers._vector_helpers import is_expected_service_unavailable
from app.domain.products.schemas import (
    ApexInventoryList,
    ApexInventorySummaryList,
    ApexOpenAPIStatus,
    ApexProductList,
    ApexRecommendation,
    ApexRecommendationRequest,
    ApexRecommendationResponse,
    ApexStoreList,
    ApexVectorStatus,
)
from app.domain.products.services import OracleVectorSearchService, ProductService, StoreService
from app.lib.di import Inject
from app.lib.settings import get_settings

logger = structlog.get_logger()

_PLACEHOLDER_PROJECT_IDS = frozenset({"demo-project", "your-project-id", "your-gcp-project-id"})
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


class ApexController(Controller):
    """JSON endpoints shaped for APEX REST Source Catalog consumption."""

    path = "/api/apex"
    tags = [_APEX_TAG]

    @get(
        "/products",
        operation_id="ApexListProducts",
        name="apex:products",
        summary="APEX Product Catalog",
    )
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
            q=_blank_to_none(q),
            category=_blank_to_none(category),
            limit=limit,
            offset=offset,
        )
        return ApexProductList(items=items, total=total, limit=limit, offset=offset)

    @get(
        "/stores",
        operation_id="ApexListStores",
        name="apex:stores",
        summary="APEX Store Catalog",
    )
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
    async def store_inventory(
        self,
        stores_service: Inject[StoreService],
        store_id: FromPath[int],
    ) -> ApexInventoryList:
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
        self,
        stores_service: Inject[StoreService],
        product_id: FromPath[int],
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
        self,
        vector_search_service: Inject[OracleVectorSearchService],
        products_service: Inject[ProductService],
        stores_service: Inject[StoreService],
        data: ApexRecommendationRequest,
    ) -> ApexRecommendationResponse:
        """Return vector recommendations, falling back to deterministic catalog search."""
        query = data.query.strip()
        if not query:
            raise ValidationException(detail="Query cannot be empty")
        limit = _bounded_limit(data.limit, default=5, maximum=25)

        try:
            matches, cache_hit, timings = await vector_search_service.similarity_search(
                query,
                k=limit,
                threshold=0.5,
                store_id=data.store_id,
            )
        except Exception as exc:
            if not is_expected_service_unavailable(exc):
                raise
            await logger.awarning("APEX vector recommendations fell back", error_type=type(exc).__name__)
            return await _fallback_recommendations(
                products_service,
                stores_service,
                query=query,
                limit=limit,
                store_id=data.store_id,
                reason=type(exc).__name__,
            )

        return ApexRecommendationResponse(
            query=query,
            mode="vector",
            items=[
                ApexRecommendation(
                    product_id=row.id,
                    name=row.name,
                    description=row.description,
                    price=row.price,
                    similarity_score=row.similarity_score,
                    store_id=row.store_id,
                    store_name=row.store_name,
                    quantity_available=row.quantity_available,
                    stock_status=row.stock_status,
                    pickup_available=row.pickup_available,
                )
                for row in matches
            ],
            total=len(matches),
            cache_hit=cache_hit,
            embedding_time_ms=round(timings.get("embedding_ms", 0.0), 2),
            oracle_time_ms=round(timings.get("oracle_ms", 0.0), 2),
        )

    @get(
        "/vector/status",
        operation_id="ApexVectorStatus",
        name="apex:vector_status",
        summary="APEX Vector Status",
    )
    async def vector_status(
        self,
        products_service: Inject[ProductService],
        vector_search_service: Inject[OracleVectorSearchService],
    ) -> ApexVectorStatus:
        """Return embedding/provider and Oracle vector readiness status."""
        readiness = await products_service.get_vector_readiness()
        settings = get_settings()
        vertex_ai_service = vector_search_service.vertex_ai_service
        embedding_model = str(getattr(vertex_ai_service, "embedding_model", settings.ai.embedding_model))
        embedding_dimensions = int(
            getattr(vertex_ai_service, "embedding_dimensions", settings.ai.embedding_dimensions)
        )
        return ApexVectorStatus(
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions,
            provider_configured=_provider_configured(),
            oracle_vector_ready=readiness.product_count > 0 and readiness.embedded_product_count > 0,
            product_count=readiness.product_count,
            embedded_product_count=readiness.embedded_product_count,
        )

    @get(
        "/openapi/status",
        operation_id="ApexOpenAPIStatus",
        name="apex:openapi_status",
        summary="APEX OpenAPI Status",
    )
    async def openapi_status(self) -> ApexOpenAPIStatus:
        """Return APEX catalog metadata and operation IDs."""
        return ApexOpenAPIStatus(
            title="Cymbal Coffee APEX REST API",
            api_version=__version__,
            base_path=self.path,
            tags=[_APEX_TAG],
            operation_ids=list(_OPERATION_IDS),
        )


async def _fallback_recommendations(
    products_service: ProductService,
    stores_service: StoreService,
    *,
    query: str,
    limit: int,
    store_id: int | None,
    reason: str,
) -> ApexRecommendationResponse:
    if store_id is not None:
        inventory = await stores_service.search_store_inventory(store_id=store_id, q=query, limit=limit)
        return ApexRecommendationResponse(
            query=query,
            mode="fallback",
            items=[
                ApexRecommendation(
                    product_id=row.product_id,
                    name=row.product_name,
                    description=row.product_description,
                    price=row.product_price if row.product_price is not None else 0.0,
                    category=row.product_category,
                    sku=row.product_sku,
                    store_id=row.store_id,
                    store_name=row.store_name,
                    quantity_available=row.quantity_available,
                    stock_status=row.stock_status,
                    pickup_available=row.pickup_available,
                )
                for row in inventory
            ],
            total=len(inventory),
            fallback_reason=reason,
        )

    products, _ = await products_service.list_apex_products(q=query, category=None, limit=limit, offset=0)
    items = [
        ApexRecommendation(
            product_id=row.id,
            name=row.name,
            description=row.description,
            price=row.price,
            category=row.category,
            sku=row.sku,
        )
        for row in products
    ]
    return ApexRecommendationResponse(
        query=query,
        mode="fallback",
        items=items,
        total=len(items),
        fallback_reason=reason,
    )


def _provider_configured() -> bool:
    settings = get_settings()
    project_id = settings.ai.project_id.strip()
    return bool(settings.ai.api_key or (project_id and project_id not in _PLACEHOLDER_PROJECT_IDS))


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

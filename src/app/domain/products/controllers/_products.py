# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from litestar import Controller, get
from litestar.di import NamedDependency
from litestar.params import FromPath, SkipValidation
from litestar.plugins.htmx import HTMXTemplate

from app.domain.products.schemas import Product, Store
from app.domain.products.services import ProductService, StoreService
from app.lib.di import Inject
from app.lib.service import FilterTypes, OffsetPagination, create_filter_dependencies


class ProductController(Controller):
    """Coffee product catalogue endpoints."""

    path = "/api/products"
    tags = ["Products"]
    dependencies = create_filter_dependencies({
        "pagination_type": "limit_offset",
        "sort_field": "name",
        "sort_order": "asc",
        "id_filter": int,
        "id_field": "id",
        "search": ["name", "description"],
        "search_ignore_case": True,
        "created_at": True,
    })

    @get("/", operation_id="ListProducts", name="products:list", summary="List Products")
    async def list_products(
        self, products_service: Inject[ProductService], filters: NamedDependency[SkipValidation[list[FilterTypes]]]
    ) -> OffsetPagination[Product]:
        """List products with pagination, search, and filtering."""
        return await products_service.list_with_count(*filters)


class StoreController(Controller):
    """Cymbal Coffee store-location endpoints."""

    path = "/api/stores"
    tags = ["Stores"]
    dependencies = create_filter_dependencies({
        "pagination_type": "limit_offset",
        "sort_field": "name",
        "sort_order": "asc",
        "id_filter": int,
        "id_field": "id",
        "search": ["name", "address", "city"],
        "search_ignore_case": True,
        "created_at": True,
    })

    @get("/", operation_id="ListStores", name="stores:list", summary="List Stores")
    async def list_stores(
        self, stores_service: Inject[StoreService], filters: NamedDependency[SkipValidation[list[FilterTypes]]]
    ) -> OffsetPagination[Store]:
        """List stores with pagination, search, and filtering."""
        return await stores_service.list_with_count(*filters)

    @get("/{store_id:int}/inventory", operation_id="StoreInventory", name="stores:inventory", summary="Store Inventory")
    async def store_inventory(self, stores_service: Inject[StoreService], store_id: FromPath[int]) -> HTMXTemplate:
        """Render current product inventory for one store."""
        inventory = await stores_service.list_store_inventory(store_id)
        return HTMXTemplate(
            template_name="partials/_inventory_list.html.j2", context={"inventory": inventory, "store_id": store_id}
        )

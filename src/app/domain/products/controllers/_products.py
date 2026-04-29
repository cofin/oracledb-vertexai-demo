# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from litestar import Controller, get
from litestar.params import Dependency

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
        self,
        products_service: Inject[ProductService],
        filters: list[FilterTypes] = Dependency(skip_validation=True),
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
        self,
        stores_service: Inject[StoreService],
        filters: list[FilterTypes] = Dependency(skip_validation=True),
    ) -> OffsetPagination[Store]:
        """List stores with pagination, search, and filtering."""
        return await stores_service.list_with_count(*filters)

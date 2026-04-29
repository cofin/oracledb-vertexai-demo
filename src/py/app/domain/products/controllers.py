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

import re
import time
import uuid
from typing import Any

from litestar import Controller, get, post
from litestar.exceptions import ValidationException
from litestar.params import Dependency

from app.domain.products import schemas as product_schemas
from app.domain.products.schemas import Product, Store
from app.domain.products.services import OracleVectorSearchService, ProductService, StoreService
from app.domain.system import schemas as system_schemas
from app.domain.system.services import MetricsService
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


class VectorController(Controller):
    """Vector search controller with JSON responses."""

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate and sanitize user message input."""
        message = re.sub(r"<[^>]+>", "", message)
        max_length = 500
        if len(message) > max_length:
            message = message[:max_length]
        message = message.replace("\x00", "").strip()

        if not message:
            raise ValidationException(detail="Message cannot be empty")

        return message

    @post(path="/api/vector-demo", name="vector.demo")
    async def vector_search_demo(
        self,
        data: product_schemas.VectorDemoRequest,
        vector_search_service: Inject[OracleVectorSearchService],
        metrics_service: Inject[MetricsService],
    ) -> dict[str, Any]:
        """Run interactive vector search demonstration."""
        query = self.validate_message(data.query)

        full_request_start = time.time()
        detailed_timings: dict[str, float] = {}

        similarity_search_start = time.time()
        results, embedding_cache_hit, vector_timings = await vector_search_service.similarity_search(query, k=5)
        detailed_timings["similarity_search_total_ms"] = (time.time() - similarity_search_start) * 1000
        detailed_timings.update(vector_timings)

        metrics_record_start = time.time()
        await metrics_service.record_search(
            system_schemas.SearchMetricsCreate(
                query_id=str(uuid.uuid4()),
                user_id="demo_user",
                search_time_ms=(time.time() - full_request_start) * 1000,
                embedding_time_ms=vector_timings["embedding_ms"],
                oracle_time_ms=vector_timings["oracle_ms"],
                similarity_score=1 - results[0]["distance"] if results else 0,
                result_count=len(results),
            )
        )
        detailed_timings["metrics_recording_ms"] = (time.time() - metrics_record_start) * 1000

        demo_results = [
            {
                "name": r["name"],
                "description": r["description"],
                "similarity": round((1 - r["distance"]) * 100, 1),
                "distance": r["distance"],
            }
            for r in results
        ]

        total_ms = (time.time() - full_request_start) * 1000
        detailed_timings["total_endpoint_ms"] = total_ms

        performance_level = (
            "excellent"
            if total_ms < 100  # noqa: PLR2004
            else "good"
            if total_ms < 500  # noqa: PLR2004
            else "needs-optimization"
        )

        return {
            "results": demo_results,
            "search_time_ms": round(total_ms, 2),
            "embedding_time_ms": round(vector_timings["embedding_ms"], 2),
            "oracle_time_ms": round(vector_timings["oracle_ms"], 2),
            "cache_hit": embedding_cache_hit,
            "performance_level": performance_level,
            "debug_timings": {k: round(v, 2) for k, v in detailed_timings.items()},
        }

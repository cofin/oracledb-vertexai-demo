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
from typing import Annotated

import structlog
from litestar import Controller, post
from litestar.enums import RequestEncodingType
from litestar.exceptions import ValidationException
from litestar.params import Body
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate

from app import schemas
from app.domain.products.services._vertex_ai import OracleVectorSearchService, VertexAIService
from app.domain.system.services import MetricsService
from app.lib.di import Inject

logger = structlog.get_logger()


class VectorController(Controller):
    """Vector Search Controller."""

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
        data: Annotated[schemas.VectorDemoRequest, Body(media_type=RequestEncodingType.URL_ENCODED)],
        vertex_ai_service: Inject[VertexAIService],
        vector_search_service: Inject[OracleVectorSearchService],
        metrics_service: Inject[MetricsService],
        request: HTMXRequest,
    ) -> HTMXTemplate:
        """Interactive vector search demonstration."""
        query = self.validate_message(data.query)

        full_request_start = time.time()
        detailed_timings: dict[str, float] = {}

        similarity_search_start = time.time()
        results, embedding_cache_hit, vector_timings = await vector_search_service.similarity_search(query, k=5)
        detailed_timings["similarity_search_total_ms"] = (time.time() - similarity_search_start) * 1000
        detailed_timings.update(vector_timings)

        metrics_record_start = time.time()
        await metrics_service.record_search(
            schemas.SearchMetricsCreate(
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

        format_results_start = time.time()
        demo_results = [
            {
                "name": r["name"],
                "description": r["description"],
                "similarity": f"{(1 - r['distance']) * 100:.1f}%",
                "distance": r["distance"],
            }
            for r in results
        ]
        detailed_timings["results_formatting_ms"] = (time.time() - format_results_start) * 1000

        pre_template_total = (time.time() - full_request_start) * 1000

        known_duration = sum([
            detailed_timings.get("similarity_search_total_ms", 0),
            detailed_timings.get("metrics_recording_ms", 0),
            detailed_timings.get("results_formatting_ms", 0),
        ])
        detailed_timings["pre_template_overhead_ms"] = pre_template_total - known_duration

        request.logger.info(
            "vector_demo_detailed_timings",
            query=query[:50],
            timings=detailed_timings,
            cache_hit=embedding_cache_hit,
        )

        performance_event = None
        perf_params = {}

        if pre_template_total < 100:  # noqa: PLR2004
            performance_event = "vector:search-fast"
            perf_params = {"level": "excellent"}
        elif pre_template_total < 500:  # noqa: PLR2004
            performance_event = "vector:search-normal"
            perf_params = {"level": "good"}
        else:
            performance_event = "vector:search-slow"
            perf_params = {"level": "needs-optimization"}

        template_start = time.time()
        response = HTMXTemplate(
            template_name="partials/_vector_results.html",
            context={
                "results": demo_results,
                "search_time": f"{pre_template_total:.0f}ms",
                "embedding_time": f"{vector_timings['embedding_ms']:.1f}ms",
                "oracle_time": f"{vector_timings['oracle_ms']:.1f}ms",
                "cache_hit": embedding_cache_hit,
                "debug_timings": {k: f"{v:.1f}ms" for k, v in detailed_timings.items()},
            },
            trigger_event=performance_event,
            params={**perf_params, "total_ms": pre_template_total},
            after="settle",
        )
        detailed_timings["template_creation_ms"] = (time.time() - template_start) * 1000

        detailed_timings["total_endpoint_ms"] = (time.time() - full_request_start) * 1000
        request.logger.info("vector_demo_final_timings", timings=detailed_timings)

        return response

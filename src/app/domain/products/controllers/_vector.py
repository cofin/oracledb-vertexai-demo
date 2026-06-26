# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

import re
import time
import uuid
from urllib.parse import quote

import structlog
from litestar import Controller, Response, get, post
from litestar.exceptions import ValidationException
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE

from app.domain.products.controllers._vector_helpers import (
    SERVICE_UNAVAILABLE_MESSAGE,
    is_expected_service_unavailable,
    payload_value,
    unavailable_plan,
    vector_query_from_request,
)
from app.domain.products.schemas import ExplainPlan, VectorDemo, VectorDemoMatch
from app.domain.products.services import OracleVectorSearchService
from app.domain.system.schemas import SearchMetricsCreate
from app.domain.system.services import MetricsService
from app.lib.di import Inject

logger = structlog.get_logger()


class VectorController(Controller):
    """Vector search controller with HTMX-aware partial / JSON responses."""

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
        vector_search_service: Inject[OracleVectorSearchService],
        metrics_service: Inject[MetricsService],
        request: HTMXRequest,
    ) -> Response | HTMXTemplate:
        """Run vector search; HTMX clients get a partial + PushUrl, SPA clients JSON."""
        data = await vector_query_from_request(request)
        query = self.validate_message(data.query)

        full_request_start = time.time()
        detailed_timings: dict[str, float] = {}

        similarity_search_start = time.time()
        try:
            results, embedding_cache_hit, vector_timings = await vector_search_service.similarity_search(query, k=5)
        except Exception as exc:
            if not is_expected_service_unavailable(exc):
                raise
            await logger.awarning("Vector search demo unavailable", error_type=type(exc).__name__)
            if request.htmx:
                return HTMXTemplate(
                    template_name="partials/explore_search_response.html.j2",
                    context={
                        "matches": [],
                        "query": query,
                        "error": SERVICE_UNAVAILABLE_MESSAGE,
                        "plan": unavailable_plan(),
                        "plan_oob": True,
                    },
                )
            return Response(
                content={
                    "status": HTTP_503_SERVICE_UNAVAILABLE,
                    "title": SERVICE_UNAVAILABLE_MESSAGE,
                    "detail": "Service Unavailable",
                },
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            )
        detailed_timings["similarity_search_total_ms"] = (time.time() - similarity_search_start) * 1000
        detailed_timings.update(vector_timings)

        metrics_record_start = time.time()
        await metrics_service.record_search(
            SearchMetricsCreate(
                query_id=str(uuid.uuid4()),
                user_id="demo_user",
                search_time_ms=(time.time() - full_request_start) * 1000,
                embedding_time_ms=vector_timings["embedding_ms"],
                oracle_time_ms=vector_timings["oracle_ms"],
                similarity_score=results[0].similarity_score if results else 0,
                result_count=len(results),
            )
        )
        detailed_timings["metrics_recording_ms"] = (time.time() - metrics_record_start) * 1000

        matches = [
            VectorDemoMatch(
                name=row.name,
                description=row.description,
                price=row.price,
                similarity=round(row.similarity_score * 100, 1),
            )
            for row in results
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

        if request.htmx:
            try:
                plan = await vector_search_service.explain_search_plan(query)
            except Exception as exc:
                if not is_expected_service_unavailable(exc):
                    raise
                await logger.awarning("Explain plan unavailable", error_type=type(exc).__name__)
                plan = unavailable_plan()
            return HTMXTemplate(
                template_name="partials/explore_search_response.html.j2",
                context={"matches": matches, "query": query, "plan": plan, "plan_oob": True},
                push_url=f"/explore?query={quote(query)}",
            )

        return Response(
            content=VectorDemo(
                results=matches,
                search_time_ms=round(total_ms, 2),
                embedding_time_ms=round(vector_timings["embedding_ms"], 2),
                oracle_time_ms=round(vector_timings["oracle_ms"], 2),
                cache_hit=embedding_cache_hit,
                performance_level=performance_level,
                debug_timings={k: round(v, 2) for k, v in detailed_timings.items()},
            )
        )

    @get(path="/api/explain-plan", name="vector.explain_plan", exclude_from_auth=True)
    async def explain_plan(
        self, request: HTMXRequest, vector_search_service: Inject[OracleVectorSearchService]
    ) -> ExplainPlan:
        """Return the Oracle EXPLAIN PLAN for the vector-search SQL."""
        query = self.validate_message(payload_value(request.query_params, "query"))
        try:
            return await vector_search_service.explain_search_plan(query)
        except Exception as exc:
            if not is_expected_service_unavailable(exc):
                raise
            await logger.awarning("Explain plan unavailable", error_type=type(exc).__name__)
            return unavailable_plan()

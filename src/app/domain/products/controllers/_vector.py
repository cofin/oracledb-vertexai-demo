# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

import re
import time
import uuid
from typing import Any
from urllib.parse import quote

from litestar import Controller, Response, get, post
from litestar.exceptions import ValidationException
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate

from app.domain.products.schemas import (
    ExplainPlan,
    VectorDemo,
    VectorDemoMatch,
    VectorQuery,
)
from app.domain.products.services import OracleVectorSearchService
from app.domain.system.schemas import SearchMetricsCreate
from app.domain.system.services import MetricsService
from app.lib.di import Inject


def _payload_value(payload: Any, key: str, default: str = "") -> str:
    getter = getattr(payload, "get", None)
    value = getter(key, default) if callable(getter) else default
    if isinstance(value, list | tuple):
        value = value[0] if value else default
    return str(value or default)


async def _vector_query_from_request(request: HTMXRequest) -> VectorQuery:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        payload = await request.form()
    return VectorQuery(query=_payload_value(payload, "query"))


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
        data = await _vector_query_from_request(request)
        query = self.validate_message(data.query)

        full_request_start = time.time()
        detailed_timings: dict[str, float] = {}

        similarity_search_start = time.time()
        results, embedding_cache_hit, vector_timings = await vector_search_service.similarity_search(query, k=5)
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
            return HTMXTemplate(
                template_name="partials/search_result_list.html.j2",
                context={"matches": matches, "query": query},
                push_url=f"/explore?q={quote(query)}",
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
            ),
        )

    @get(path="/api/explain-plan", name="vector.explain_plan", exclude_from_auth=True)
    async def explain_plan(
        self,
        query: str,
        vector_search_service: Inject[OracleVectorSearchService],
    ) -> ExplainPlan:
        """Return the Oracle EXPLAIN PLAN for the vector-search SQL."""
        return await vector_search_service.explain_search_plan(self.validate_message(query))

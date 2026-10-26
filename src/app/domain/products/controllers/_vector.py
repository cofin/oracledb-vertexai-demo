# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Vector search controller for HTMX demo, explain plan, and MCP search tool."""

import re
import time
import uuid
from typing import Annotated, Any, ClassVar
from urllib.parse import quote

import structlog
from litestar import Response, get, post
from litestar.exceptions import ValidationException
from litestar.params import QueryParameter
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE
from litestar_htmx import HTMXRequest, HTMXTemplate
from litestar_security import AuthenticationPolicy, PublicController, exclude

from app.domain.products.schemas import ExplainPlan, VectorDemo, VectorDemoMatch, VectorQuery
from app.domain.products.services import (
    SERVICE_UNAVAILABLE_MESSAGE,
    OracleVectorSearchService,
    build_explore_telemetry_context,
    build_vector_demo_matches,
    unavailable_plan,
)
from app.domain.system.schemas import SearchMetricsCreate
from app.domain.system.services import MetricsService
from app.lib.di import Inject
from app.lib.exceptions import AIServiceUnconfigured, is_expected_service_unavailable

__all__ = ("VectorController",)

logger = structlog.get_logger()
_PERF_EXCELLENT_MS: float = 100.0
_PERF_GOOD_MS: float = 500.0


class VectorController(PublicController):
    """Vector search controller with HTMX-aware partial / JSON responses and MCP tools."""

    auth: ClassVar[AuthenticationPolicy] = exclude()

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

    @post(path="/api/vector-demo", name="vector.demo", opt={"exclude_from_csrf": False})
    async def vector_search_demo(
        self,
        vector_search_service: Inject[OracleVectorSearchService],
        metrics_service: Inject[MetricsService],
        request: HTMXRequest,
    ) -> Response | HTMXTemplate:
        """Run vector search; HTMX clients get a partial + PushUrl, SPA clients JSON."""
        data = await _vector_query_from_request(request)
        query = self.validate_message(data.query)

        full_request_start = time.perf_counter()
        detailed_timings: dict[str, float] = {}

        similarity_search_start = time.perf_counter()
        try:
            results, embedding_cache_hit, vector_timings = await vector_search_service.similarity_search(query, k=5)
        except Exception as exc:
            if not is_expected_service_unavailable(exc):
                raise
            await logger.awarning("Vector search demo unavailable", error_type=type(exc).__name__)
            if request.htmx:
                telemetry_ctx = build_explore_telemetry_context(query, matches=[])
                return HTMXTemplate(
                    template_name="partials/explore_search_response.html.j2",
                    context={
                        "matches": [],
                        "query": query,
                        "error": SERVICE_UNAVAILABLE_MESSAGE,
                        "plan": unavailable_plan(),
                        "plan_oob": True,
                        **telemetry_ctx,
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
        detailed_timings["similarity_search_total_ms"] = (time.perf_counter() - similarity_search_start) * 1000
        detailed_timings.update(vector_timings)

        metrics_record_start = time.perf_counter()
        await metrics_service.record_search(
            SearchMetricsCreate(
                query_id=str(uuid.uuid4()),
                user_id="demo_user",
                search_time_ms=(time.perf_counter() - full_request_start) * 1000,
                embedding_time_ms=vector_timings["embedding_ms"],
                oracle_time_ms=vector_timings["oracle_ms"],
                similarity_score=results[0].similarity_score if results else 0,
                result_count=len(results),
            )
        )
        detailed_timings["metrics_recording_ms"] = (time.perf_counter() - metrics_record_start) * 1000

        matches = build_vector_demo_matches(results)
        telemetry_ctx = build_explore_telemetry_context(
            query,
            matches=matches,
            embedding_ms=vector_timings["embedding_ms"],
            oracle_ms=vector_timings["oracle_ms"],
            cache_hit=embedding_cache_hit,
        )

        total_ms = (time.perf_counter() - full_request_start) * 1000
        detailed_timings["total_endpoint_ms"] = total_ms

        performance_level = (
            "excellent"
            if total_ms < _PERF_EXCELLENT_MS
            else "good"
            if total_ms < _PERF_GOOD_MS
            else "needs-optimization"
        )

        if request.htmx:
            plan: ExplainPlan | None = None
            plan_error: str | None = None
            try:
                plan = await vector_search_service.explain_search_plan(query)
            except Exception as exc:
                if not is_expected_service_unavailable(exc):
                    raise
                plan_error = type(exc).__name__
            if plan is None:
                await logger.awarning("Explain plan unavailable", error_type=plan_error)
                plan = unavailable_plan()
            return HTMXTemplate(
                template_name="partials/explore_search_response.html.j2",
                context={"matches": matches, "query": query, "plan": plan, "plan_oob": True, **telemetry_ctx},
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
                search_mode="hybrid",
                rrf_k=int(telemetry_ctx["rrf_k"]),
                oracle_text_query=telemetry_ctx["oracle_text_query"],
                sql_phases=telemetry_ctx["sql_phases"],
            )
        )

    @get(path="/api/explain-plan", name="vector.explain_plan")
    async def explain_plan(
        self, request: HTMXRequest, vector_search_service: Inject[OracleVectorSearchService]
    ) -> ExplainPlan:
        """Return the Oracle EXPLAIN PLAN for the hybrid RRF or vector-search SQL."""
        query = self.validate_message(_payload_value(request.query_params, "query"))
        mode = _payload_value(request.query_params, "mode").strip().lower()
        plan_error: str | None = None
        try:
            if mode == "vector":
                return await vector_search_service.explain_search_plan(query, mode="vector")
            return await vector_search_service.explain_search_plan(query)
        except Exception as exc:
            if not is_expected_service_unavailable(exc):
                raise
            plan_error = type(exc).__name__
        await logger.awarning("Explain plan unavailable", error_type=plan_error)
        return unavailable_plan()

    @get(
        path="/api/vector-search", name="vector.search", summary="Search Products by Vector", mcp_tool="search_products"
    )
    async def vector_search(
        self,
        q: Annotated[str, QueryParameter(name="query", min_length=1, max_length=500)],
        vector_search_service: Inject[OracleVectorSearchService],
        limit: Annotated[int, QueryParameter(name="limit", ge=1, le=20)] = 5,
    ) -> list[VectorDemoMatch]:
        """Perform semantic vector search for coffee products.

        Args:
            q: Natural language query string passed via the ``query`` URL parameter.
            vector_search_service: OracleVectorSearchService instance.
            limit: Maximum number of matching items to return.

        Returns:
            List of matching products with calculated similarity percentages.
        """
        clean_query = self.validate_message(q)
        try:
            results, _, _ = await vector_search_service.similarity_search(clean_query, k=limit)
        except Exception as exc:
            if is_expected_service_unavailable(exc):
                raise AIServiceUnconfigured(SERVICE_UNAVAILABLE_MESSAGE) from exc
            raise
        return build_vector_demo_matches(results)


def _payload_value(payload: Any, key: str, default: str = "") -> str:
    getter = getattr(payload, "get", None)
    value = getter(key, default) if callable(getter) else default
    if isinstance(value, list | tuple):
        value = value[0] if value else default
    return str(value or default)


async def _vector_query_from_request(request: HTMXRequest) -> VectorQuery:
    content_type = request.headers.get("content-type", "")
    payload = await request.json() if "application/json" in content_type else await request.form()
    return VectorQuery(query=_payload_value(payload, "query"))

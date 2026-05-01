# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Private helpers for vector controller request parsing and fallback responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from google.genai import errors as genai_errors

from app.domain.products.schemas import ExplainPlan, VectorQuery

if TYPE_CHECKING:
    from litestar.plugins.htmx import HTMXRequest

SERVICE_UNAVAILABLE_MESSAGE = "Vector search is unavailable. Check Vertex AI and Oracle configuration, then retry."


def is_expected_service_unavailable(exc: BaseException) -> bool:
    text = str(exc).lower()
    if isinstance(exc, genai_errors.ClientError):
        return any(
            marker in text
            for marker in (
                "api key",
                "credentials",
                "permission_denied",
                "service_disabled",
                "forbidden",
                "unauthorized",
            )
        )
    return any(
        marker in text
        for marker in (
            "api key",
            "credentials",
            "permission_denied",
            "service_disabled",
            "vertex ai api has not been used",
        )
    )


def payload_value(payload: Any, key: str, default: str = "") -> str:
    getter = getattr(payload, "get", None)
    value = getter(key, default) if callable(getter) else default
    if isinstance(value, list | tuple):
        value = value[0] if value else default
    return str(value or default)


def unavailable_plan(message: str = SERVICE_UNAVAILABLE_MESSAGE) -> ExplainPlan:
    return ExplainPlan(plan_lines=[message], plan_summary="Plan unavailable")


async def vector_query_from_request(request: HTMXRequest) -> VectorQuery:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        payload = await request.form()
    return VectorQuery(query=payload_value(payload, "query"))

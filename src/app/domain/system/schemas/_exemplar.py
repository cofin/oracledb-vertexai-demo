# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — used in handler-visible schema; Litestar OpenAPI needs runtime ref

from app.lib.schema import CamelizedBaseStruct


class IntentExemplar(CamelizedBaseStruct, omit_defaults=True):
    """Intent classification training example."""

    id: int
    intent: str
    phrase: str
    confidence_threshold: float | None = None
    usage_count: int = 0
    embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

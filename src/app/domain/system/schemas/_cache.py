# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.lib.schema import CamelizedBaseStruct

if TYPE_CHECKING:
    from datetime import datetime


class ResponseCache(CamelizedBaseStruct, omit_defaults=True):
    """Response cache entry."""

    id: int
    cache_key: str
    response_data: dict[str, Any]
    created_at: datetime
    expires_at: datetime | None = None


class EmbeddingCache(CamelizedBaseStruct, omit_defaults=True):
    """Embedding cache entry."""

    id: int
    text_hash: str
    embedding: list[float]
    model: str
    created_at: datetime
    last_accessed: datetime
    hit_count: int = 0

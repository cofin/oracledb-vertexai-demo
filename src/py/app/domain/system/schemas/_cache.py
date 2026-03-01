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

from __future__ import annotations

from datetime import datetime
from typing import Any

import msgspec


class ResponseCache(msgspec.Struct, omit_defaults=True):
    """Response cache entry."""

    id: int
    cache_key: str
    response_data: dict[str, Any]
    created_at: datetime
    expires_at: datetime | None = None


class EmbeddingCache(msgspec.Struct, omit_defaults=True):
    """Embedding cache entry."""

    id: int
    text_hash: str
    embedding: list[float]
    model: str
    created_at: datetime
    last_accessed: datetime
    hit_count: int = 0

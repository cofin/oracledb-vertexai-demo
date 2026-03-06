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

from typing import TYPE_CHECKING, Any

from app.lib.schema import CamelizedBaseStruct

if TYPE_CHECKING:
    from datetime import datetime


class Product(CamelizedBaseStruct, omit_defaults=True):
    """Product entity from database."""

    id: int
    name: str
    price: float
    description: str
    category: str | None = None
    sku: str | None = None
    in_stock: bool = True
    metadata: dict[str, Any] | None = None
    embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Store(CamelizedBaseStruct, omit_defaults=True):
    """Store location entity from database."""

    id: int
    name: str
    address: str
    created_at: datetime
    updated_at: datetime
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    phone: str | None = None
    hours: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class VectorDemoRequest(CamelizedBaseStruct, omit_defaults=True):
    """Vector search demo request."""

    query: str


class VectorDemoResult(CamelizedBaseStruct, omit_defaults=True):
    """Vector search demo result."""

    product_name: str
    description: str
    similarity_score: float
    search_time_ms: float

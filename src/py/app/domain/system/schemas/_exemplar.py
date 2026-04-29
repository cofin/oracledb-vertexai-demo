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

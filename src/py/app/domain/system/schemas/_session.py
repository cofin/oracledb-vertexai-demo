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
from uuid import UUID

import msgspec


class UserSessionCreate(msgspec.Struct, omit_defaults=True):
    """Session creation payload."""

    user_id: str
    data: dict = {}


class UserSessionRead(msgspec.Struct, omit_defaults=True):
    """Session response payload."""

    id: UUID
    session_id: str
    user_id: str
    data: dict
    expires_at: datetime
    created_at: datetime


class HistoryMeta(msgspec.Struct, omit_defaults=True):
    """History metadata."""

    conversation_id: str
    user_id: str

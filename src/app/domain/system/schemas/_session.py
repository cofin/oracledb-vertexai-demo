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

from typing import TYPE_CHECKING

from app.lib.schema import CamelizedBaseStruct

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class UserSessionCreate(CamelizedBaseStruct, omit_defaults=True):
    """Session row to persist."""

    user_id: str
    data: dict = {}


class UserSession(CamelizedBaseStruct, omit_defaults=True):
    """A persisted session row."""

    id: UUID
    session_id: str
    user_id: str
    data: dict
    expires_at: datetime
    created_at: datetime


class HistoryMeta(CamelizedBaseStruct, omit_defaults=True):
    """Conversation-history metadata for a user."""

    conversation_id: str
    user_id: str

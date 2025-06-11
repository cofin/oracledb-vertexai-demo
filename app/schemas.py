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

import msgspec

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

__all__ = (
    "BaseStruct",
    "CamelizedBaseSchema",
    "CamelizedBaseStruct",
    "ChatConversationCreate",
    "ChatConversationRead",
    "ChatMessage",
    "CoffeeChatMessage",
    "CoffeeChatReply",
    "HistoryMeta",
    "Message",
    "SearchMetricsCreate",
    "UserSessionCreate",
    "UserSessionRead",
    "camel_case",
)


class BaseStruct(msgspec.Struct):
    def to_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__struct_fields__ if getattr(self, f, None) != msgspec.UNSET}


class CamelizedBaseStruct(BaseStruct, rename="camel"):
    """Camelized Base Struct"""


class Message(CamelizedBaseStruct):
    message: str


def camel_case(string: str) -> str:
    """Convert a string to camel case.

    Args:
        string (str): The string to convert

    Returns:
        str: The string converted to camel case
    """
    return "".join(word if index == 0 else word.capitalize() for index, word in enumerate(string.split("_")))


class CoffeeChatMessage(msgspec.Struct):
    """Chat message input DTO."""

    message: str
    persona: str = "enthusiast"


# Oracle-specific DTOs


class UserSessionCreate(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Session creation payload."""

    user_id: str
    data: dict = {}


class UserSessionRead(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Session response payload."""

    id: UUID
    session_id: str
    user_id: str
    data: dict
    expires_at: datetime
    created_at: datetime


class ChatConversationCreate(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Conversation creation payload."""

    session_id: UUID
    user_id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    message_metadata: dict = {}


class ChatConversationRead(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Conversation response payload."""

    id: UUID
    user_id: str
    role: str
    content: str
    message_metadata: dict
    created_at: datetime


class SearchMetricsCreate(msgspec.Struct, gc=False, array_like=True, omit_defaults=True, kw_only=True):
    """Metrics creation payload."""

    query_id: str
    user_id: str | None = None
    search_time_ms: float
    embedding_time_ms: float
    oracle_time_ms: float
    similarity_score: float | None = None
    result_count: int


class ChatMessage(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Individual chat message."""

    message: str
    source: str  # 'human' | 'ai' | 'system'


class CoffeeChatReply(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Complete chat response."""

    message: str
    messages: list[ChatMessage]
    answer: str
    query_id: str
    search_metrics: dict = {}


# Legacy TypedDict for compatibility (to be removed)
class HistoryMeta(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """History metadata."""

    conversation_id: str
    user_id: str

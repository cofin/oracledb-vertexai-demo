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


from datetime import datetime
from uuid import UUID

from app.lib.schema import CamelizedBaseStruct


class SimilarIntent(CamelizedBaseStruct, omit_defaults=True):
    """Represents a similar intent found by vector search."""

    intent: str
    phrase: str
    similarity: float
    confidence_threshold: float


class Intent(CamelizedBaseStruct, omit_defaults=True):
    """A classified intent for an incoming chat query."""

    intent: str
    confidence: float
    exemplar_phrase: str
    embedding_cache_hit: bool
    fallback_used: bool


class CoffeeChatMessage(CamelizedBaseStruct):
    """Inbound user message for the barista chat."""

    message: str
    persona: str = "enthusiast"


class ChatConversationCreate(CamelizedBaseStruct, omit_defaults=True):
    """Conversation row to persist."""

    session_id: UUID
    user_id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    message_metadata: dict = {}


class ChatConversation(CamelizedBaseStruct, omit_defaults=True):
    """A persisted conversation row."""

    id: UUID
    user_id: str
    role: str
    content: str
    message_metadata: dict
    created_at: datetime


class ChatMessage(CamelizedBaseStruct, omit_defaults=True):
    """Individual chat message."""

    message: str
    source: str  # 'human' | 'ai' | 'system'


class CoffeeChatReply(CamelizedBaseStruct, omit_defaults=True):
    """Complete chat response."""

    message: str
    messages: list[ChatMessage]
    answer: str
    query_id: str
    search_metrics: dict = {}
    from_cache: bool = False
    embedding_cache_hit: bool = False
    intent_detected: str = "GENERAL_CONVERSATION"

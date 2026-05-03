# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from uuid import UUID

from app.lib.schema import CamelizedBaseStruct


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
    store_results: list[dict]
    inventory_results: list[dict]
    map_actions: list[dict]
    location_context: dict
    search_metrics: dict = {}
    sql_phases: list[dict] = []
    from_cache: bool = False
    embedding_cache_hit: bool = False
    intent_detected: str = "GENERAL_CONVERSATION"

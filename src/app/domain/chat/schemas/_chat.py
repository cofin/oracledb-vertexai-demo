# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from app.lib.schema import CamelizedBaseStruct


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

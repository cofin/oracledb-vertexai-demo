# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Private ADK event/history coercion helpers."""

from __future__ import annotations

from typing import Any

from app.domain.chat.schemas import ChatMessage


def _coerce_history_messages(value: Any) -> list[ChatMessage]:
    if not isinstance(value, list):
        return []
    messages: list[ChatMessage] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "")
        message = str(item.get("message") or "")
        if source in {"human", "ai"} and message:
            messages.append(ChatMessage(source=source, message=message))
    return messages


def _event_content_text(event: Any) -> str:
    """Extract text from an ADK event."""
    if not event.content or not event.content.parts:
        return ""
    return "".join(str(part.text) for part in event.content.parts if getattr(part, "text", None))


def _event_history_messages(events: Any) -> list[ChatMessage]:
    if not isinstance(events, list):
        return []
    messages: list[ChatMessage] = []
    for event in events:
        if getattr(event, "partial", False):
            continue
        text = _event_content_text(event).strip()
        if not text:
            continue
        role = getattr(getattr(event, "content", None), "role", None)
        author = str(getattr(event, "author", "") or "")
        if role == "user":
            messages.append(ChatMessage(source="human", message=text))
        elif role == "model" and author in {"coffee_turn", "CoffeeAssistant", "model"}:
            messages.append(ChatMessage(source="ai", message=text))
    return messages

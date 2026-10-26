# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat session identity helpers bridging browser sessions to AI runtime sessions."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar_htmx import HTMXRequest

__all__ = (
    "CHAT_SESSION_KEY",
    "CHAT_USER_KEY",
    "chat_session_identity",
    "clear_chat_session_id",
    "get_chat_owner_id",
    "get_or_create_chat_session_id",
)

CHAT_SESSION_KEY = "chat_session_id"
CHAT_USER_KEY = "chat_user_id"


def get_or_create_chat_session_id(request: HTMXRequest) -> str:
    """Return the active chat session identifier, creating and storing one if absent."""
    session = request.session
    session_id = session.get(CHAT_SESSION_KEY)
    if not isinstance(session_id, str) or not session_id:
        session_id = request.get_session_id() or str(uuid.uuid4())
        session[CHAT_SESSION_KEY] = session_id
    return session_id


def get_chat_owner_id(request: HTMXRequest) -> str:
    """Return the stable browser-scoped chat owner identifier for the active session."""
    session_id = get_or_create_chat_session_id(request)
    session = request.session
    user_id = session.get(CHAT_USER_KEY)
    if not isinstance(user_id, str) or not user_id:
        user_id = f"web:{session_id}"
        session[CHAT_USER_KEY] = user_id
    return user_id


def chat_session_identity(request: HTMXRequest) -> tuple[str, str]:
    """Return ``(owner_id, session_id)`` derived from the Litestar browser session."""
    session_id = get_or_create_chat_session_id(request)
    owner_id = get_chat_owner_id(request)
    return owner_id, session_id


def clear_chat_session_id(request: HTMXRequest) -> None:
    """Remove persisted chat session and owner identifiers from the browser session."""
    request.session.pop(CHAT_SESSION_KEY, None)
    request.session.pop(CHAT_USER_KEY, None)

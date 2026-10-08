# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat session identity helpers bridging browser sessions to AI runtime sessions."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar_htmx import HTMXRequest

CHAT_SESSION_KEY = "chat_session_id"
CHAT_USER_KEY = "chat_user_id"

ADK_SESSION_KEY = CHAT_SESSION_KEY
ADK_USER_KEY = CHAT_USER_KEY


def chat_session_identity(request: HTMXRequest) -> tuple[str, str]:
    """Bridge Litestar's server-side session identity to AI runtime session backend.

    Returns:
        The chat user id and session id derived from the Litestar session.
    """
    session = request.session
    session_id = session.get(CHAT_SESSION_KEY)
    if not isinstance(session_id, str) or not session_id:
        session_id = request.get_session_id() or str(uuid.uuid4())
        session[CHAT_SESSION_KEY] = session_id

    user_id = session.get(CHAT_USER_KEY)
    if not isinstance(user_id, str) or not user_id:
        user_id = f"web:{session_id}"
        session[CHAT_USER_KEY] = user_id

    return user_id, session_id


def clear_chat_session_identity(request: HTMXRequest) -> None:
    """Remove the chat identity bridge from the Litestar browser session."""
    request.session.pop(CHAT_SESSION_KEY, None)
    request.session.pop(CHAT_USER_KEY, None)


adk_session_identity = chat_session_identity
clear_adk_session_identity = clear_chat_session_identity

__all__ = (
    "ADK_SESSION_KEY",
    "ADK_USER_KEY",
    "CHAT_SESSION_KEY",
    "CHAT_USER_KEY",
    "adk_session_identity",
    "chat_session_identity",
    "clear_adk_session_identity",
    "clear_chat_session_identity",
)

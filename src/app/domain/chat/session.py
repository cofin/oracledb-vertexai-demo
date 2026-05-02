# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar.plugins.htmx import HTMXRequest

ADK_SESSION_KEY = "adk_session_id"
ADK_USER_KEY = "adk_user_id"


def adk_session_identity(request: HTMXRequest) -> tuple[str, str]:
    """Bridge Litestar's server-side session identity to ADK's session backend.

    Returns:
        The ADK user id and session id derived from the Litestar session.
    """
    session = request.session
    session_id = session.get(ADK_SESSION_KEY)
    if not isinstance(session_id, str) or not session_id:
        session_id = request.get_session_id() or str(uuid.uuid4())
        session[ADK_SESSION_KEY] = session_id

    user_id = session.get(ADK_USER_KEY)
    if not isinstance(user_id, str) or not user_id:
        user_id = f"web:{session_id}"
        session[ADK_USER_KEY] = user_id

    return user_id, session_id


def clear_adk_session_identity(request: HTMXRequest) -> None:
    """Remove the ADK identity bridge from the Litestar browser session."""
    request.session.pop(ADK_SESSION_KEY, None)
    request.session.pop(ADK_USER_KEY, None)

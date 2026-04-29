# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

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

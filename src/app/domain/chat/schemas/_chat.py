# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat message schema representations."""

from typing import Literal

from app.lib.schema import CamelizedBaseStruct

__all__ = ("ChatMessage",)


class ChatMessage(CamelizedBaseStruct, omit_defaults=True):
    """Individual chat message within a session."""

    message: str
    source: Literal["human", "ai", "system"]

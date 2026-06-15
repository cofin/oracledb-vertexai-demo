# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from app.lib.schema import CamelizedBaseStruct


class ChatMessage(CamelizedBaseStruct, omit_defaults=True):
    """Individual chat message."""

    message: str
    source: str  # 'human' | 'ai' | 'system'

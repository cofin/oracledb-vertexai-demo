# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A2A 1.0 Agent-to-Agent protocol package."""

from app.domain.ai.a2a._card import COFFEE_AGENT_CARD, DEFAULT_A2A_BASE_URL, build_agent_card
from app.domain.ai.a2a._executor import (
    ANONYMOUS_A2A_USER,
    CoffeeAgentExecutor,
    build_a2a_call_context,
    resolve_a2a_user_id,
)

__all__ = (
    "ANONYMOUS_A2A_USER",
    "COFFEE_AGENT_CARD",
    "DEFAULT_A2A_BASE_URL",
    "CoffeeAgentExecutor",
    "build_a2a_call_context",
    "build_agent_card",
    "resolve_a2a_user_id",
)

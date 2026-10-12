# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A2A 1.0 Agent-to-Agent protocol package."""

from app.domain.ai.a2a.card import COFFEE_AGENT_CARD, build_agent_card
from app.domain.ai.a2a.executor import CoffeeAgentExecutor, build_a2a_call_context, resolve_a2a_user_id

__all__ = (
    "COFFEE_AGENT_CARD",
    "CoffeeAgentExecutor",
    "build_a2a_call_context",
    "build_agent_card",
    "resolve_a2a_user_id",
)

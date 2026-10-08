# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A2A 1.0 Agent-to-Agent protocol package."""

from app.domain.ai.a2a.card import COFFEE_AGENT_CARD
from app.domain.ai.a2a.executor import CoffeeAgentExecutor

__all__ = ("COFFEE_AGENT_CARD", "CoffeeAgentExecutor")

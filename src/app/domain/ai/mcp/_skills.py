# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""SkillController declaration exposing Cymbal Coffee barista skills over MCP and A2A."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar_mcp import SkillController, tool
from litestar_security import public

from app.domain.system.services import BASE_SYSTEM_INSTRUCTION

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ("CoffeeSkillController",)


class CoffeeSkillController(SkillController):
    """MCP and A2A skill controller for the Cymbal Coffee barista catalog and store guide."""

    name = "cymbal-coffee-barista"
    description = "Cymbal Coffee barista skill providing grounded menu, recipe, and store availability guidance."
    tags: Sequence[str] | None = ("coffee", "barista", "inventory", "oracle-26ai")
    examples = ("What dark roasts do you recommend?", "Which Dallas stores have Espresso Blend in stock?")
    instructions = BASE_SYSTEM_INSTRUCTION
    opt = {"auth": public()}

    @tool(
        name="describe_barista_capabilities",
        description="Describe the Cymbal Coffee barista agent skills, grounded routes, and supported tools.",
    )
    def describe_capabilities(self) -> dict[str, Any]:
        """Return structured metadata describing the Cymbal Coffee barista skill."""
        return {
            "skill": self.to_agent_skill(),
            "instructions": self.get_instructions(),
            "routes": ["PRODUCT_RAG", "PRODUCT_AVAILABILITY", "STORE_LOCATION", "ORDER_STATUS", "GENERAL_CONVERSATION"],
        }

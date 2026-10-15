# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""PromptController declaration exposing reusable Cymbal Coffee prompts over MCP."""

from __future__ import annotations

from litestar.params import FromQuery
from litestar_mcp import PromptController, PromptMessage, prompt
from litestar_security import public

from app.domain.system.services import BASE_SYSTEM_INSTRUCTION

__all__ = ("CoffeePromptController",)


class CoffeePromptController(PromptController):
    """Declarative MCP prompt controller for Cymbal Coffee recommendations and store checks."""

    prefix = "coffee"
    instructions = BASE_SYSTEM_INSTRUCTION
    opt = {"auth": public()}

    @prompt(
        name="barista-recommendation",
        title="Barista Recommendation",
        description="Generate a grounded Cymbal Coffee drink recommendation from customer preferences.",
    )
    def barista_recommendation(
        self, preference: FromQuery[str] = "bold dark roast", dietary_notes: FromQuery[str] = ""
    ) -> list[PromptMessage]:
        """Build a prompt requesting a grounded drink recommendation."""
        dietary_clause = f" Dietary notes: {dietary_notes.strip()}." if dietary_notes.strip() else ""
        text = (
            f"Recommend a Cymbal Coffee drink matching '{preference.strip()}'.{dietary_clause} "
            "Use the grounded menu catalog and include price and tasting notes."
        )
        return [PromptMessage.user(text)]

    @prompt(
        name="store-inventory-check",
        title="Store Inventory Check",
        description="Check Cymbal Coffee store locations and product availability for a city or neighborhood.",
    )
    def store_inventory_check(
        self, product_name: FromQuery[str] = "Espresso", city: FromQuery[str] = "Dallas"
    ) -> list[PromptMessage]:
        """Build a prompt checking store availability for a Cymbal Coffee product."""
        text = (
            f"Check which Cymbal Coffee stores in {city.strip()} currently have "
            f"'{product_name.strip()}' in stock, including store addresses and Google Maps directions."
        )
        return [PromptMessage.user(text)]

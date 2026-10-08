# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""AgentCard declaration for A2A 1.0 discovery."""

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

COFFEE_AGENT_CARD = AgentCard(
    name="Cymbal Coffee Barista Agent",
    description="Intelligent agent for specialty coffee recommendations, brew recipes, and store inventory.",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=True),
    skills=[
        AgentSkill(
            id="coffee_recommendation",
            name="Coffee Recommendations",
            description="Recommends roasts and beverages grounded in the Cymbal Coffee catalog.",
            tags=["coffee", "recommendation"],
        ),
        AgentSkill(
            id="store_inventory",
            name="Store Inventory & Pickup",
            description="Checks product availability and store hours across Dallas-Fort Worth locations.",
            tags=["inventory", "stores"],
        ),
    ],
    supported_interfaces=[
        AgentInterface(url="http://localhost:8000/a2a", protocol_binding="JSONRPC", protocol_version="1.0")
    ],
)

__all__ = ("COFFEE_AGENT_CARD",)

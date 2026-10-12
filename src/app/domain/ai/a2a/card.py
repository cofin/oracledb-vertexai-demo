# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""AgentCard declaration for A2A 1.0 discovery."""

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

__all__ = ("COFFEE_AGENT_CARD", "DEFAULT_A2A_BASE_URL", "build_agent_card")

DEFAULT_A2A_BASE_URL = "http://localhost:8000"


def build_agent_card(base_url: str = DEFAULT_A2A_BASE_URL) -> AgentCard:
    """Build the A2A 1.0 AgentCard for the Cymbal Coffee Barista agent.

    Args:
        base_url: Base server URL used to advertise the JSON-RPC /a2a interface.

    Returns:
        Configured AgentCard instance.
    """
    normalized_base = base_url.rstrip("/") or DEFAULT_A2A_BASE_URL
    return AgentCard(
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
            AgentInterface(url=f"{normalized_base}/a2a", protocol_binding="JSONRPC", protocol_version="1.0")
        ],
    )


COFFEE_AGENT_CARD = build_agent_card()

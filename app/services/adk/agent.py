"""Core ADK Agent Implementations.

This module implements the Google ADK agents that form the coffee assistant system.
Now using a single unified agent for better performance.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from app.config import settings
from app.services.adk.prompts import UNIFIED_AGENT_INSTRUCTION
from app.services.adk.tools import (
    classify_intent,
    get_product_details,
    search_products_by_vector,
)

# Single Unified Agent - Handles all requests directly without routing overhead
CoffeeAssistantAgent = LlmAgent(
    name="CoffeeAssistant",
    description="The main coffee assistant for Cymbal Coffee. Handles all customer requests directly with product search, recommendations, and coffee knowledge.",
    instruction=UNIFIED_AGENT_INSTRUCTION,
    model=settings.vertex_ai.CHAT_MODEL,
    # All tools available to the single agent
    tools=[classify_intent, search_products_by_vector, get_product_details],
    # No sub_agents - single agent handles everything directly
)

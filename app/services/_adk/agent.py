"""Core ADK Agent Implementations for the modern architecture."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from app.config import settings
from app.services._adk.prompts import SYSTEM_INSTRUCTION
from app.services._adk.tools import ALL_TOOLS

CoffeeAssistantAgent = LlmAgent(
    name="CoffeeAssistant",
    description="The main coffee assistant for Cymbal Coffee. Handles all customer requests directly with product search, recommendations, and coffee knowledge.",
    instruction=SYSTEM_INSTRUCTION,
    model=settings.vertex_ai.CHAT_MODEL,
    tools=ALL_TOOLS,
)

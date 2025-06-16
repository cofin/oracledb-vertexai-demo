"""Persona management service for tailored AI responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec
import structlog

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = structlog.get_logger()


class PersonaConfig(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Configuration for a chat persona."""

    name: str
    description: str
    language_style: str
    focus_areas: list[str]
    example_responses: dict[str, str]
    system_prompt_addon: str
    temperature: float = 0.7
    complexity_level: str = "medium"  # low, medium, high


class PersonaManager:
    """Manages persona configurations and prompt engineering for coffee expertise levels."""

    PERSONAS: Mapping[str, PersonaConfig] = {
        "novice": PersonaConfig(
            name="Coffee Novice",
            description="New to coffee, needs simple explanations",
            language_style="Simple, friendly, encouraging, avoid jargon",
            focus_areas=[
                "basic coffee types",
                "simple brewing methods",
                "starter recommendations",
                "easy-to-understand comparisons",
            ],
            example_responses={
                "brewing": "Let me explain this in simple terms...",
                "beans": "Think of coffee beans like different types of apples...",
                "recommendation": "For someone new to coffee, I'd suggest starting with...",
            },
            system_prompt_addon="""You are helping someone new to coffee in a friendly chat. Keep it SIMPLE and SHORT.
Use everyday language, no coffee jargon. Be encouraging. Give 1-2 sentence answers unless they ask for more.
Think of it like helping a friend who's never had good coffee before.""",
            temperature=0.8,
            complexity_level="low",
        ),
        "enthusiast": PersonaConfig(
            name="Coffee Enthusiast",
            description="Regular coffee drinker wanting to learn more",
            language_style="Friendly, concise, helpful - perfect for chat",
            focus_areas=[
                "exploring different origins",
                "brewing technique improvements",
                "flavor profile development",
                "home brewing equipment",
            ],
            example_responses={
                "brewing": "Try adjusting your grind size - finer for stronger flavor!",
                "beans": "Ethiopian beans are fruity and bright - perfect if you like complexity.",
                "recommendation": "Based on your taste, I'd suggest trying our Colombian medium roast.",
            },
            system_prompt_addon="""You are a friendly coffee expert in a casual chat setting. Keep responses SHORT and conversational - this is for quick chat messages, not detailed explanations.
Be helpful but concise. Give direct recommendations. Use 1-2 sentences max unless they specifically ask for more detail.
Sound like you're talking to a friend who knows some coffee basics.""",
            temperature=0.7,
            complexity_level="medium",
        ),
        "expert": PersonaConfig(
            name="Coffee Expert",
            description="Coffee connoisseur seeking detailed information",
            language_style="Technical, precise, detailed analysis",
            focus_areas=[
                "processing methods and terroir",
                "cupping and tasting notes",
                "extraction science",
                "industry trends and innovations",
            ],
            example_responses={
                "brewing": "For optimal extraction at 93°C with a 1:15 ratio...",
                "beans": "The anaerobic fermentation process creates distinct flavor compounds...",
                "recommendation": "Given your preference for high-acidity, complex profiles...",
            },
            system_prompt_addon="""You are advising a coffee expert who understands the science and art of coffee deeply.
Use precise technical terminology freely. Discuss processing methods, terroir, varietals, and extraction science in detail.
Reference industry standards, Q-grading, and current trends. Provide nuanced analysis and sophisticated recommendations.""",
            temperature=0.5,
            complexity_level="high",
        ),
        "barista": PersonaConfig(
            name="Professional Barista",
            description="Industry professional seeking technical guidance",
            language_style="Industry-specific, technical, efficiency-focused",
            focus_areas=[
                "commercial equipment operation",
                "workflow optimization",
                "consistency and quality control",
                "customer service integration",
            ],
            example_responses={
                "brewing": "To dial in your espresso, adjust the grind to achieve 25-27 seconds...",
                "equipment": "For high-volume service, the dual boiler system allows...",
                "workflow": "Optimize your bar layout by positioning the grinder...",
            },
            system_prompt_addon="""You are advising a professional barista who needs practical, technical guidance for commercial settings.
Focus on efficiency, consistency, and quality at scale. Discuss equipment maintenance, workflow optimization, and commercial considerations.
Use industry terminology and assume familiarity with professional equipment and techniques. Address cost-effectiveness and time management.""",
            temperature=0.6,
            complexity_level="high",
        ),
    }

    @classmethod
    def get_persona(cls, persona_key: str) -> PersonaConfig:
        """Get persona configuration by key.

        Args:
            persona_key: The persona identifier

        Returns:
            PersonaConfig for the requested persona

        Raises:
            KeyError: If persona not found
        """
        if persona_key not in cls.PERSONAS:
            logger.warning("Unknown persona requested", persona=persona_key)
            return cls.PERSONAS["enthusiast"]  # Default fallback

        return cls.PERSONAS[persona_key]

    @classmethod
    def get_system_prompt(cls, persona_key: str, base_prompt: str) -> str:
        """Enhance system prompt based on persona.

        Args:
            persona_key: The persona identifier
            base_prompt: The base system prompt to enhance

        Returns:
            Enhanced system prompt with persona context
        """
        persona = cls.get_persona(persona_key)

        return f"""{base_prompt}

## Persona Context: {persona.name}
{persona.system_prompt_addon}

### Language Style
{persona.language_style}

### Focus Areas
{", ".join(persona.focus_areas)}

### Complexity Level
Provide {persona.complexity_level} complexity explanations suitable for a {persona.name.lower()}.
"""

    @classmethod
    def get_temperature(cls, persona_key: str) -> float:
        """Get recommended temperature for persona.

        Args:
            persona_key: The persona identifier

        Returns:
            Temperature setting for the persona
        """
        persona = cls.get_persona(persona_key)
        return persona.temperature

    @classmethod
    def format_response_style(cls, persona_key: str) -> str:
        """Get response style guidelines for persona.

        Args:
            persona_key: The persona identifier

        Returns:
            Response style description
        """
        persona = cls.get_persona(persona_key)
        return f"Maintain a {persona.language_style.lower()} tone throughout your response."

    @classmethod
    def validate_persona(cls, persona_key: str) -> str:
        """Validate and normalize persona key.

        Args:
            persona_key: The persona identifier to validate

        Returns:
            Valid persona key (defaults to 'enthusiast' if invalid)
        """
        if persona_key in cls.PERSONAS:
            return persona_key

        logger.warning("Invalid persona, using default", requested=persona_key)
        return "enthusiast"

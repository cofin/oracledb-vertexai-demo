# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat persona definition schema."""

import msgspec

from app.lib.schema import FrozenBaseStruct

__all__ = ("PersonaDefinition",)


class PersonaDefinition(FrozenBaseStruct, frozen=True):
    """Immutable configuration for a chat persona."""

    name: str
    description: str
    language_style: str
    focus_areas: list[str]
    system_prompt_addon: str
    example_responses: dict[str, str] = msgspec.field(default_factory=dict)
    temperature: float = 0.7
    complexity_level: str = "medium"

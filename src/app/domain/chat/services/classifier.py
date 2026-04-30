# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Flash-Lite intent classifier using ``text/x.enum`` structured output."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from google.genai import types

if TYPE_CHECKING:
    from google.genai import Client


class IntentLabel(str, Enum):
    """Coffee-domain intent labels."""

    PRODUCT_RAG = "PRODUCT_RAG"
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    STORE_LOCATION = "STORE_LOCATION"
    ORDER_STATUS = "ORDER_STATUS"


INTENT_VALUES: list[str] = [m.value for m in IntentLabel]

_SYSTEM_INSTRUCTION = "Classify the user's coffee-related intent. Return exactly one label."


class FlashLiteIntentClassifier:
    """Single-call intent classifier backed by ``gemini-2.5-flash-lite``."""

    def __init__(self, client: Client, model: str = "gemini-2.5-flash-lite") -> None:
        self._client = client
        self._model = model

    async def classify(self, phrase: str) -> IntentLabel:
        """Return the intent label for ``phrase``."""
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=phrase,
            config=types.GenerateContentConfig(
                response_mime_type="text/x.enum",
                response_schema={"type": "STRING", "enum": INTENT_VALUES},
                system_instruction=_SYSTEM_INSTRUCTION,
            ),
        )
        return IntentLabel(response.text)


__all__ = ("INTENT_VALUES", "FlashLiteIntentClassifier", "IntentLabel")

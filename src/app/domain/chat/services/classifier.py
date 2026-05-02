# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Flash-Lite intent classifier using ``text/x.enum`` structured output."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from google.genai import types

if TYPE_CHECKING:
    from google.genai import Client


class IntentLabel(StrEnum):
    """Coffee-domain intent labels."""

    PRODUCT_RAG = "PRODUCT_RAG"
    PRODUCT_AVAILABILITY = "PRODUCT_AVAILABILITY"
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    STORE_LOCATION = "STORE_LOCATION"
    ORDER_STATUS = "ORDER_STATUS"


INTENT_VALUES: list[str] = [m.value for m in IntentLabel]

_SYSTEM_INSTRUCTION = """Classify the user's coffee-related intent. Return exactly one label.

Labels:
- PRODUCT_RAG: menu, catalog, product, price, roast, caffeine, preparation, substitution, breakfast/food pairing, or recommendation questions. Choose this for idioms and vague preference requests such as "breakfast", "something bold", "wake me up", "surprise me", "what's good today", "what should I get", "do you have decaf", or "what is on the menu".
- PRODUCT_AVAILABILITY: store-level product stock, pickup availability, or where to buy a specific item near a city, ZIP code, store, or browser location. Examples: "Where can I pick up cold brew near me", "is espresso available in Dallas", "which cafe has nitro cold brew", or "do you have muffins in 75201".
- STORE_LOCATION: store locations, hours, addresses, nearest cafe, pickup location, or directions. Examples: "Find a store near Dallas", "where is your Seattle store", "hours for Austin", or "directions to Cymbal Coffee".
- ORDER_STATUS: order status, delivery status, pickup status, refunds, or changes to an existing order.
- GENERAL_CONVERSATION: greetings, thanks, small talk, or non-menu conversation.

When a coffee or menu request is ambiguous, choose PRODUCT_RAG."""


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
                temperature=0,
            ),
        )
        return IntentLabel(str(response.text).strip())


__all__ = ("INTENT_VALUES", "FlashLiteIntentClassifier", "IntentLabel")

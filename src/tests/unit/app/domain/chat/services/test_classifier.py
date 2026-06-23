# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin the FlashLiteIntentClassifier contract."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.chat.services.classifier import INTENT_VALUES, FlashLiteIntentClassifier, IntentLabel

pytestmark = pytest.mark.anyio


def test_intent_label_values_match_text_x_enum_pin() -> None:
    """IntentLabel must enumerate the labels asserted in test_adk2_surface_pin."""
    assert {m.value for m in IntentLabel} == {
        "PRODUCT_RAG",
        "PRODUCT_AVAILABILITY",
        "GENERAL_CONVERSATION",
        "STORE_LOCATION",
        "ORDER_STATUS",
    }
    assert [m.value for m in IntentLabel] == INTENT_VALUES


async def test_classifier_returns_enum_member_for_valid_text() -> None:
    response = MagicMock()
    response.text = "PRODUCT_RAG"
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.models = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)

    classifier = FlashLiteIntentClassifier(client)
    result = await classifier.classify("dark roast espresso")

    assert result is IntentLabel.PRODUCT_RAG


async def test_classifier_maps_store_location_text_to_label() -> None:
    response = MagicMock(text="STORE_LOCATION")
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.models = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)

    classifier = FlashLiteIntentClassifier(client, model="gemini-3.1-flash-lite")

    result = await classifier.classify("where is the nearest cafe")

    assert result is IntentLabel.STORE_LOCATION


async def test_classifier_raises_on_unknown_label() -> None:
    response = MagicMock(text="WHATEVER")
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.models = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)

    classifier = FlashLiteIntentClassifier(client)

    with pytest.raises(ValueError):
        await classifier.classify("noise")

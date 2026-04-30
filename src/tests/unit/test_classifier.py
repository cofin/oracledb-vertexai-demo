# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin the FlashLiteIntentClassifier contract."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.chat.services.classifier import (
    INTENT_VALUES,
    FlashLiteIntentClassifier,
    IntentLabel,
)


def test_intent_label_values_match_text_x_enum_pin() -> None:
    """IntentLabel must enumerate the four labels asserted in test_adk2_surface_pin."""
    assert {m.value for m in IntentLabel} == {
        "PRODUCT_RAG",
        "GENERAL_CONVERSATION",
        "STORE_LOCATION",
        "ORDER_STATUS",
    }
    assert [m.value for m in IntentLabel] == INTENT_VALUES


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_classifier_passes_text_x_enum_config() -> None:
    response = MagicMock(text="STORE_LOCATION")
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.models = MagicMock()
    captured: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return response

    client.aio.models.generate_content = _capture
    classifier = FlashLiteIntentClassifier(client, model="gemini-2.5-flash-lite")

    await classifier.classify("where is the nearest cafe")

    assert captured["model"] == "gemini-2.5-flash-lite"
    assert captured["contents"] == "where is the nearest cafe"
    cfg = captured["config"]
    assert cfg.response_mime_type == "text/x.enum"
    assert cfg.response_schema == {"type": "STRING", "enum": INTENT_VALUES}
    assert cfg.temperature == 0
    assert "what is on the menu" in cfg.system_instruction
    assert "something bold" in cfg.system_instruction
    assert "When a coffee or menu request is ambiguous, choose PRODUCT_RAG" in cfg.system_instruction


@pytest.mark.asyncio
async def test_classifier_raises_on_unknown_label() -> None:
    response = MagicMock(text="WHATEVER")
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.models = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)

    classifier = FlashLiteIntentClassifier(client)

    with pytest.raises(ValueError):
        await classifier.classify("noise")

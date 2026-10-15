# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for `VertexAIService` `gemini-embedding-2` prompt instruction formatting."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from app.domain.products.services import VertexAIService

pytestmark = pytest.mark.anyio


async def test_gemini_embedding_2_uses_prompt_instruction_not_task_type() -> None:
    """Verify `gemini-embedding-2` embeds with task instruction prefix and 3072 output dimensionality."""
    embed_content = AsyncMock(return_value=SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2])]))
    cache_service: Any = SimpleNamespace(get_embedding=AsyncMock(return_value=None), save_embedding=AsyncMock())
    service = VertexAIService(
        client=cast("Any", SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)))),
        model="gemini-3.8-flash",
        embedding_model="gemini-embedding-2",
        embedding_dimensions=3072,
        cache_service=cache_service,
    )

    result = await service.get_text_embedding("cold brew", embedding_purpose="query")

    assert result == [0.1, 0.2]
    assert embed_content.await_args is not None
    kwargs = embed_content.await_args.kwargs
    assert kwargs["model"] == "gemini-embedding-2"
    assert kwargs["contents"].startswith("Task: Generate an embedding for a search query")
    assert kwargs["contents"].endswith("cold brew")
    assert kwargs["config"].output_dimensionality == 3072
    assert getattr(kwargs["config"], "task_type", None) is None


async def test_get_text_embedding_empty_response_returns_tuple_when_cache_status_requested() -> None:
    """Verify `get_text_embedding(..., return_cache_status=True)` returns `(None, False)` on empty embeddings."""
    embed_content = AsyncMock(return_value=SimpleNamespace(embeddings=[]))
    cache_service: Any = SimpleNamespace(get_embedding=AsyncMock(return_value=None), save_embedding=AsyncMock())
    service = VertexAIService(
        client=cast("Any", SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)))),
        model="gemini-3.8-flash",
        embedding_model="gemini-embedding-2",
        embedding_dimensions=3072,
        cache_service=cache_service,
    )

    result = await service.get_text_embedding("cold brew", embedding_purpose="query", return_cache_status=True)

    assert result == (None, False)
    cache_service.save_embedding.assert_not_awaited()

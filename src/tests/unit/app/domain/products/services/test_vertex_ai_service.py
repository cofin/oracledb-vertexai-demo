# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.products.services import VertexAIService

pytestmark = pytest.mark.anyio


async def test_gemini_embedding_2_uses_prompt_instruction_not_task_type() -> None:
    embed_content = AsyncMock(return_value=SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2])]))
    cache_service = SimpleNamespace(get_embedding=AsyncMock(return_value=None), save_embedding=AsyncMock())
    service = VertexAIService(
        client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content))),
        model="gemini-2.5-flash-lite",
        embedding_model="gemini-embedding-2-preview",
        embedding_dimensions=3072,
        cache_service=cache_service,
    )

    result = await service.get_text_embedding("cold brew", embedding_purpose="query")

    assert result == [0.1, 0.2]
    kwargs = embed_content.await_args.kwargs
    assert kwargs["model"] == "gemini-embedding-2-preview"
    assert kwargs["contents"].startswith("Task: Generate an embedding for a search query")
    assert kwargs["contents"].endswith("cold brew")
    assert kwargs["config"].output_dimensionality == 3072
    assert getattr(kwargs["config"], "task_type", None) is None

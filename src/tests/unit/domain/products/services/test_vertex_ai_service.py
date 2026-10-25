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


async def test_vertex_ai_service_embed_missing_products_runs_pure_async_batches() -> None:
    """Verify `VertexAIService.embed_missing_products` embeds products and routes in slices without CLI coupling."""
    embed_content = AsyncMock(return_value=SimpleNamespace(embeddings=[SimpleNamespace(values=[0.25] * 3072)]))
    cache_service: Any = SimpleNamespace(get_embedding=AsyncMock(return_value=None), save_embedding=AsyncMock())
    service = VertexAIService(
        client=cast("Any", SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)))),
        model="gemini-3.8-flash",
        embedding_model="gemini-embedding-2",
        embedding_dimensions=3072,
        cache_service=cache_service,
    )
    assert not hasattr(service, "__dict__")

    product_service = AsyncMock()
    product_service.get_products_for_embedding.return_value = (
        [
            {"id": 1, "name": "Cold Brew", "description": "Smooth dark roast"},
            {"id": 2, "name": "Cortado", "description": "Equal espresso and steamed milk"},
        ],
        2,
    )
    product_service.get_chat_routes_for_embedding.return_value = (
        [
            {
                "id": 10,
                "route_label": "PRODUCT_RAG",
                "title": "Coffee Menu",
                "exemplar_text": "What dark roasts do you serve?",
                "keywords": "coffee dark roast menu",
            }
        ],
        1,
    )
    product_service.update_embedding.side_effect = [True, False]
    product_service.update_chat_route_embedding.return_value = True

    batches_seen: list[tuple[str, int, int, int, int]] = []
    summary = await service.embed_missing_products(
        product_service,
        batch_size=1,
        force=True,
        on_batch=lambda kind, idx, total, ok, err: batches_seen.append((kind, idx, total, ok, err)),
    )

    assert summary == {"products_embedded": 1, "routes_embedded": 1, "errors": 1}
    assert batches_seen == [("products", 1, 2, 1, 0), ("products", 2, 2, 0, 1), ("chat_routes", 1, 1, 1, 0)]
    product_service.get_products_for_embedding.assert_awaited_once_with(force=True)
    product_service.get_chat_routes_for_embedding.assert_awaited_once_with(force=True)

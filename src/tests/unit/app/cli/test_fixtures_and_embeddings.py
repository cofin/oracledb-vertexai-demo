# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Behavioral unit tests for hybrid Oracle Text migration DDL, chat_route fixtures, and CLI embedding helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import msgspec
import pytest

from app.cli._helpers.embeddings import generate_product_embeddings
from app.db.utils import COFFEE_SHOP_TABLES
from tests.support.paths import APP_ROOT

MIGRATION_0002 = APP_ROOT / "db" / "migrations" / "0002_agent_runtime_and_hybrid_search.sql"
CHAT_ROUTE_FIXTURE = APP_ROOT / "db" / "fixtures" / "chat_route.json"
EXPECTED_ROUTE_LABELS = frozenset(
    {
        "PRODUCT_RAG",
        "PRODUCT_AVAILABILITY",
        "STORE_LOCATION",
        "ORDER_STATUS",
        "GENERAL_CONVERSATION",
    }
)


def test_migration_0002_includes_multi_column_datastore_and_chat_route() -> None:
    """Verify migration 0002 defines MULTI_COLUMN_DATASTORE preferences, hybrid text indexes, and chat_route."""
    sql_text = MIGRATION_0002.read_text(encoding="utf-8")

    assert "product_search_ds" in sql_text
    assert "store_search_ds" in sql_text
    assert "MULTI_COLUMN_DATASTORE" in sql_text
    assert "product_hybrid_ctx_idx" in sql_text
    assert "store_hybrid_ctx_idx" in sql_text
    assert "CREATE TABLE chat_route" in sql_text
    assert "chat_route_ctx_idx" in sql_text
    assert "chat_route_embedding_idx" in sql_text
    assert "SYNC (ON COMMIT)" in sql_text


def test_fixture_tables_include_chat_route_and_fixture_file_has_25_exemplars() -> None:
    """Verify chat_route is registered in COFFEE_SHOP_TABLES and seeded with 25 3072-d exemplars."""
    assert "chat_route" in COFFEE_SHOP_TABLES
    assert CHAT_ROUTE_FIXTURE.exists(), "chat_route.json fixture must exist"

    records = msgspec.json.decode(CHAT_ROUTE_FIXTURE.read_bytes())
    assert isinstance(records, list)
    assert len(records) == 25

    labels_seen = {row["route_label"] for row in records}
    assert labels_seen == EXPECTED_ROUTE_LABELS

    for row in records:
        assert row["id"] >= 1
        assert row["title"]
        assert row["exemplar_text"]
        assert row["keywords"]
        assert isinstance(row["embedding"], list)
        assert len(row["embedding"]) == 3072


@pytest.mark.anyio
async def test_generate_product_embeddings_embeds_products_and_chat_routes() -> None:
    """Verify generate_product_embeddings embeds both product and chat_route records with document purpose."""
    mock_product_service = AsyncMock()
    mock_product_service.get_products_for_embedding.return_value = (
        [{"id": 1, "name": "Ethiopian Yirgacheffe", "description": "Floral citrus"}],
        1,
    )
    mock_product_service.update_embedding.return_value = True
    mock_product_service.get_chat_routes_for_embedding.return_value = (
        [
            {
                "id": 10,
                "route_label": "PRODUCT_RAG",
                "title": "Fruity coffee recommendations",
                "exemplar_text": "What fruity or floral light roast coffees do you recommend?",
                "keywords": "recommend menu coffee roast flavor",
            }
        ],
        1,
    )
    mock_product_service.update_chat_route_embedding.return_value = True

    mock_vertex = AsyncMock()
    mock_vertex.get_text_embedding.return_value = [0.01] * 3072

    await generate_product_embeddings(
        batch_size=10,
        force=True,
        product_service=mock_product_service,
        vertex_ai_service=mock_vertex,
    )

    mock_product_service.get_products_for_embedding.assert_awaited_once_with(force=True)
    mock_product_service.update_embedding.assert_awaited_once_with(1, [0.01] * 3072)
    mock_product_service.get_chat_routes_for_embedding.assert_awaited_once_with(force=True)
    mock_product_service.update_chat_route_embedding.assert_awaited_once_with(10, [0.01] * 3072)
    assert mock_vertex.get_text_embedding.await_count == 2
    for call in mock_vertex.get_text_embedding.await_args_list:
        assert call.kwargs.get("embedding_purpose") == "document"

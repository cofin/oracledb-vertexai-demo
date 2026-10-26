# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Behavioral unit tests for hybrid Oracle Text migration DDL, chat_route fixtures, and CLI batch validation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import msgspec
import pytest
import rich_click as click

from app.cli.commands import _run_bulk_embed, _upgrade_database
from app.db.utils import COFFEE_SHOP_TABLES
from tests.support.paths import APP_ROOT

MIGRATION_0001 = APP_ROOT / "db" / "migrations" / "0001_cymball_coffee_products.sql"
CHAT_ROUTE_FIXTURE = APP_ROOT / "db" / "fixtures" / "chat_route.json"
EXPECTED_ROUTE_LABELS = frozenset({
    "PRODUCT_RAG",
    "PRODUCT_AVAILABILITY",
    "STORE_LOCATION",
    "ORDER_STATUS",
    "GENERAL_CONVERSATION",
})


def test_migration_0001_includes_multi_column_datastore_and_chat_route() -> None:
    """Verify baseline migration 0001 defines MULTI_COLUMN_DATASTORE preferences, hybrid text indexes, and chat_route."""
    sql_text = MIGRATION_0001.read_text(encoding="utf-8")

    assert "product_search_ds" in sql_text
    assert "store_search_ds" in sql_text
    assert "MULTI_COLUMN_DATASTORE" in sql_text
    assert "product_hybrid_ctx_idx" in sql_text
    assert "store_hybrid_ctx_idx" in sql_text
    assert "CREATE TABLE chat_route" in sql_text
    assert "chat_route_ctx_idx" in sql_text
    assert "chat_route_embedding_idx" in sql_text
    assert "SYNC (ON COMMIT)" in sql_text
    assert "idx_agent_event_session_seq" not in sql_text


@pytest.mark.anyio
async def test_upgrade_database_aborts_before_loading_fixtures_on_migration_failure() -> None:
    """Verify _upgrade_database raises ClickException and skips load_fixtures when a migration fails."""
    mock_commands = MagicMock()
    mock_commands._apply_single_migration = AsyncMock(return_value=None)

    async def _fake_upgrade(*, revision: str, dry_run: bool) -> None:
        _ = (revision, dry_run)
        await mock_commands._apply_single_migration()

    mock_commands.upgrade = AsyncMock(side_effect=_fake_upgrade)

    with (
        patch("app.cli.commands.create_migration_commands", return_value=mock_commands),
        patch("app.cli.commands.load_fixtures", new_callable=AsyncMock) as mock_load_fixtures,
        pytest.raises(click.ClickException, match="Database migration failed"),
    ):
        await _upgrade_database("head", no_fixtures=False, dry_run=False)

    mock_load_fixtures.assert_not_awaited()


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
async def test_run_bulk_embed_rejects_non_positive_batch_size() -> None:
    """Verify _run_bulk_embed validates batch_size >= 1 before enqueuing background work."""
    queue_service = AsyncMock()

    with pytest.raises(click.ClickException, match=r"Batch size must be at least 1\."):
        await _run_bulk_embed(batch_size=0, force=False, queue_service=queue_service)

    queue_service.enqueue.assert_not_awaited()

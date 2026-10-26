# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Behavioral unit tests for Oracle 26ai background jobs, task container scoping, and CLI dispatch."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner
from dishka import Scope
from litestar_queues import QueueService, get_scheduled_tasks, get_task_registry
from litestar_queues.models import QueuedTaskRecord
from litestar_queues.task import TaskResult

from app.cli import commands as cli_commands
from app.cli.main import cli
from app.domain.products.jobs import embed_missing_records
from app.domain.products.services import ProductService, VertexAIService
from app.domain.system.jobs import cleanup_expired_cache_and_sessions
from app.domain.system.services import CacheService
from app.lib.jobs import get_task_container, request_container_var, task_container_scope, worker_container_var


@pytest.mark.anyio
async def test_task_container_scope_resolves_request_and_worker_containers() -> None:
    """Verify task_container_scope reuses request_container_var or enters Scope.REQUEST on worker_container_var."""
    fake_request_container = MagicMock()
    req_token = request_container_var.set(fake_request_container)
    try:
        async with task_container_scope() as resolved:
            assert resolved is fake_request_container
            assert get_task_container() is fake_request_container
    finally:
        request_container_var.reset(req_token)

    scoped_child = MagicMock()
    worker_scope_cm = AsyncMock()
    worker_scope_cm.__aenter__.return_value = scoped_child
    worker_scope_cm.__aexit__.return_value = False
    fake_worker_container = MagicMock(return_value=worker_scope_cm)

    worker_token = worker_container_var.set(fake_worker_container)
    try:
        async with task_container_scope() as resolved:
            assert resolved is scoped_child
            assert get_task_container() is scoped_child
        fake_worker_container.assert_called_once_with(scope=Scope.REQUEST)
    finally:
        worker_container_var.reset(worker_token)


@pytest.mark.anyio
async def test_cleanup_expired_cache_and_sessions_executes_maintenance() -> None:
    """Verify system.cache_cleanup deletes expired responses and stale agent sessions."""
    registry = get_task_registry()
    schedules = get_scheduled_tasks()
    assert "system.cache_cleanup" in registry
    assert registry["system.cache_cleanup"].queue == "maintenance"
    assert "system.cache_cleanup" in schedules
    assert schedules["system.cache_cleanup"].cron == "*/15 * * * *"

    mock_cache_service = AsyncMock(spec=CacheService)
    mock_cache_service.delete_expired_responses.return_value = 4
    mock_cache_service.delete_stale_agent_sessions.return_value = 2

    fake_container = AsyncMock()

    async def _get_dep(dep_type: Any) -> Any:
        if dep_type is CacheService:
            return mock_cache_service
        raise KeyError(dep_type)

    fake_container.get.side_effect = _get_dep
    req_token = request_container_var.set(fake_container)
    try:
        result = await cleanup_expired_cache_and_sessions(retention_days=7)
    finally:
        request_container_var.reset(req_token)

    assert result == {"expired_responses_deleted": 4, "stale_sessions_deleted": 2}
    mock_cache_service.delete_expired_responses.assert_awaited_once()
    mock_cache_service.delete_stale_agent_sessions.assert_awaited_once_with(retention_days=7)


def test_products_jobs_module_has_zero_cli_imports() -> None:
    """Verify `app.domain.products.jobs` does not import `app.cli` helpers."""
    jobs_path = Path(__file__).resolve().parents[3] / "app" / "domain" / "products" / "jobs.py"
    jobs_tree = ast.parse(jobs_path.read_text(encoding="utf-8"), filename=str(jobs_path))
    cli_imports = [
        node.module
        for node in ast.walk(jobs_tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("app.cli")
    ]
    assert cli_imports == []


@pytest.mark.anyio
async def test_embed_missing_records_embeds_products_and_chat_routes() -> None:
    """Verify products.embed_missing delegates directly to VertexAIService.embed_missing_products."""

    registry = get_task_registry()
    assert "products.embed_missing" in registry
    assert registry["products.embed_missing"].queue == "embeddings"
    assert registry["products.embed_missing"].retries == 3

    mock_product_service = AsyncMock(spec=ProductService)
    mock_product_service.get_products_for_embedding.return_value = (
        [{"id": 10, "name": "Decaf Espresso", "description": "Velvety decaf roast"}],
        1,
    )
    mock_product_service.get_chat_routes_for_embedding.return_value = (
        [
            {
                "id": 20,
                "route_label": "STORE_LOCATION",
                "title": "Store Finder",
                "exemplar_text": "Where is the nearest store?",
                "keywords": "store location near me",
            }
        ],
        1,
    )
    mock_product_service.update_embedding.return_value = True
    mock_product_service.update_chat_route_embedding.return_value = True

    embed_content = AsyncMock(return_value=SimpleNamespace(embeddings=[SimpleNamespace(values=[0.25] * 3072)]))
    cache_service: Any = SimpleNamespace(get_embedding=AsyncMock(return_value=None), save_embedding=AsyncMock())
    vertex_service = VertexAIService(
        client=cast("Any", SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)))),
        model="gemini-3.8-flash",
        embedding_model="gemini-embedding-2",
        embedding_dimensions=3072,
        cache_service=cache_service,
    )

    fake_container = AsyncMock()

    async def _get_dep(dep_type: Any) -> Any:
        if dep_type is ProductService:
            return mock_product_service
        if dep_type is VertexAIService:
            return vertex_service
        raise KeyError(dep_type)

    fake_container.get.side_effect = _get_dep
    req_token = request_container_var.set(fake_container)
    try:
        summary = await embed_missing_records(batch_size=25, force=False)
    finally:
        request_container_var.reset(req_token)

    assert summary == {"products_embedded": 1, "routes_embedded": 1, "errors": 0}
    mock_product_service.get_products_for_embedding.assert_awaited_once_with(force=False)
    mock_product_service.get_chat_routes_for_embedding.assert_awaited_once_with(force=False)
    mock_product_service.update_embedding.assert_awaited_once_with(10, [0.25] * 3072)
    mock_product_service.update_chat_route_embedding.assert_awaited_once_with(20, [0.25] * 3072)


@pytest.mark.anyio
async def test_bulk_embed_runs_through_queue_service_with_immediate_execution() -> None:
    """Verify coffee bulk-embed always runs products.embed_missing through QueueService with immediate execution."""
    assert cli_commands is not None
    mock_queue_service = AsyncMock(spec=QueueService)
    fake_record = MagicMock(spec=QueuedTaskRecord)
    fake_record.id = "00000000-0000-0000-0000-000000000042"
    fake_record.status = "completed"
    fake_result = AsyncMock(spec=TaskResult)
    fake_result.id = fake_record.id
    fake_result.status = "completed"
    fake_result.record = fake_record
    mock_queue_service.enqueue.return_value = fake_result

    await cli_commands._run_bulk_embed(batch_size=25, force=True, queue_service=mock_queue_service)

    mock_queue_service.enqueue.assert_awaited_once_with(
        embed_missing_records, batch_size=25, force=True, execution_backend="immediate"
    )
    fake_result.refresh.assert_awaited_once()


def test_cli_exposes_worker_and_queues_commands() -> None:
    """Verify coffee CLI registers worker, queues, bulk-embed, and run --no-worker."""
    assert cli_commands is not None
    runner = CliRunner()
    help_res = runner.invoke(cli, ["--help"])
    assert help_res.exit_code == 0
    assert "worker" in help_res.output
    assert "queues" in help_res.output

    embed_help = runner.invoke(cli, ["bulk-embed", "--help"])
    assert embed_help.exit_code == 0
    assert "--batch-size" in embed_help.output
    assert "--force" in embed_help.output
    assert "--enqueue" not in embed_help.output

    run_help = runner.invoke(cli, ["run", "--help"])
    assert run_help.exit_code == 0
    assert "--no-worker" in run_help.output

# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ADK chat workflow integration coverage against Oracle-backed SQLSpec stores."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from google.adk.workflow._function_node import FunctionNode
from google.genai import types
from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

from app.config import db
from app.domain.chat.services.adk import ADKRunner, AgentToolsService
from app.domain.chat.services.classifier import IntentLabel
from app.domain.products.services import ProductService, StoreService
from app.domain.system.services import CacheService, MetricsService, PersonaManager

if TYPE_CHECKING:
    from sqlspec.adapters.oracledb import OracleAsyncDriver

pytestmark = pytest.mark.anyio


def _seed_embedding() -> list[float]:
    """Return a deterministic, non-zero 3072-dimension vector."""
    return [0.5] * 3072


async def _seed_product_with_embedding(driver: OracleAsyncDriver) -> None:
    """Attach the deterministic vector to the fixture marker product."""
    result = await driver.select_one_or_none(
        "SELECT id FROM product WHERE sku = :sku",
        sku="SEED-SKU-001",
    )
    assert result is not None, "integration conftest should seed SEED-SKU-001"

    await driver.execute(
        "UPDATE product SET embedding = :embedding WHERE id = :id",
        embedding=_seed_embedding(),
        id=int(result["id"]),
    )
    await driver.commit()


class FakeIntentClassifier:
    """Deterministic classifier that records the phrase it received."""

    def __init__(self) -> None:
        self.phrases: list[str] = []

    async def classify(self, phrase: str) -> IntentLabel:
        self.phrases.append(phrase)
        return IntentLabel.PRODUCT_RAG


class FakeVertexAIService:
    """Embedding service stub that keeps the Oracle/vector path live."""

    model = "integration-test-chat-model"

    async def get_text_embedding(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
        return_cache_status: bool = False,
    ) -> Any:
        del text, task_type
        embedding = _seed_embedding()
        return (embedding, True) if return_cache_status else embedding


def _fake_llm_agent(**kwargs: Any) -> FunctionNode:
    """Replace the external model call with a deterministic ADK node."""
    tools = {tool.__name__: tool for tool in kwargs["tools"]}

    async def coffee_turn(ctx: Any, node_input: str) -> types.Content:
        del ctx
        result = await tools["search_products_by_vector"](
            node_input,
            limit=5,
            similarity_threshold=0.5,
        )
        products = result["products"]
        assert products, "product RAG must return at least one Oracle-backed match"
        return types.Content(
            role="model",
            parts=[types.Part(text=f"{products[0]['name']} is a good fit for a bold coffee request.")],
        )

    return FunctionNode(func=coffee_turn, name=str(kwargs["name"]), parameter_binding="state")


async def test_chat_workflow_populates_result_shape_with_oracle_backed_rag(
    monkeypatch: pytest.MonkeyPatch,
    driver: OracleAsyncDriver,
) -> None:
    await _seed_product_with_embedding(driver)
    session_id = f"integration-chat-workflow-{uuid.uuid4().hex}"
    query = f"I need something that will wake me up {uuid.uuid4().hex}"

    from app.domain.chat.services import adk as adk_module

    monkeypatch.setattr(adk_module, "LlmAgent", _fake_llm_agent)
    configured = SimpleNamespace(
        vertex_ai=SimpleNamespace(
            PROJECT_ID="test-project",
            API_KEY=None,
            CHAT_MODEL="gemini-2.5-flash-lite",
        )
    )
    monkeypatch.setattr(adk_module, "get_settings", lambda: configured)

    store = OracleAsyncADKStore(config=db)
    await store.ensure_tables()
    session_service = SQLSpecSessionService(store)
    classifier = FakeIntentClassifier()
    runner = ADKRunner(
        session_service=session_service,
        classifier=classifier,  # type: ignore[arg-type]
        persona_manager=PersonaManager(),
    )
    tools_service = AgentToolsService(
        driver=driver,
        product_service=ProductService(driver),
        metrics_service=MetricsService(driver),
        vertex_ai_service=FakeVertexAIService(),  # type: ignore[arg-type]
        store_service=StoreService(driver),
        cache_service=CacheService(driver),
    )

    result = await runner.process_request(
        query=query,
        user_id="integration-user",
        session_id=session_id,
        persona="enthusiast",
        tools_service=tools_service,
    )

    assert set(result) == {
        "answer",
        "session_id",
        "response_time_ms",
        "intent_detected",
        "search_metrics",
        "from_cache",
        "embedding_cache_hit",
    }
    assert result["session_id"] == session_id
    assert result["intent_detected"] == IntentLabel.PRODUCT_RAG.value
    assert result["answer"]
    assert result["search_metrics"]["products_found"] >= 1
    assert result["search_metrics"]["results_count"] == result["search_metrics"]["products_found"]
    assert result["response_time_ms"] < 4000
    assert result["from_cache"] is False
    assert result["embedding_cache_hit"] is True
    assert classifier.phrases == [query]

    persisted = await session_service.get_session(
        app_name="coffee_assistant",
        user_id="integration-user",
        session_id=session_id,
    )
    assert persisted is not None
    assert persisted.state["intent"] == IntentLabel.PRODUCT_RAG.value

# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ADK chat workflow integration coverage against Oracle-backed SQLSpec stores."""

from __future__ import annotations

import json
import re
import uuid
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from google.adk.workflow import FunctionNode
from google.genai import types
from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

from app.domain.chat.services.adk import ADKRunner, AgentToolsService
from app.domain.chat.services.classifier import IntentLabel
from app.domain.products.services import ProductService, StoreService
from app.domain.system.services import CacheService, MetricsService, PersonaManager

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlspec.adapters.oracledb import OracleAsyncDriver

pytestmark = pytest.mark.anyio


def _seed_embedding() -> list[float]:
    """Return a deterministic, non-zero 3072-dimension vector."""
    return [0.5] * 3072


async def _seed_product_with_embedding(driver: OracleAsyncDriver, sku: str) -> None:
    """Insert a uniquely keyed embedded product for the workflow turn."""
    await driver.execute(
        """
        INSERT INTO product (name, description, price, category, sku, in_stock, embedding)
        VALUES (:name, :description, :price, :category, :sku, TRUE, :embedding)
        """,
        name=f"Workflow Test Roast {sku}",
        description="Bold coffee seeded for chat workflow integration tests",
        price=11.99,
        category="Coffee",
        sku=sku,
        embedding=_seed_embedding(),
    )
    await driver.commit()


class FakeIntentClassifier:
    """Deterministic classifier that records the phrase it received."""

    def __init__(self) -> None:
        self.phrases: list[str] = []

    async def classify(self, phrase: str) -> IntentLabel:
        self.phrases.append(phrase)
        return IntentLabel.PRODUCT_RAG


class _FakeGenAiModels:
    """Stub Gemini models endpoint that returns a guard-passing product selection."""

    async def generate_content(self, **kwargs: Any) -> Any:
        contents = str(kwargs.get("contents") or "")
        product_id = re.search(r"id=([^;]+);", contents)
        payload = {
            "mode": "recommend",
            "off_menu_term": "",
            "selected_product_ids": [product_id.group(1)] if product_id else [],
        }
        return SimpleNamespace(text=json.dumps(payload))


class FakeVertexAIService:
    """Embedding service stub that keeps the Oracle/vector path live."""

    model = "integration-test-chat-model"

    def __init__(self) -> None:
        self.client = SimpleNamespace(aio=SimpleNamespace(models=_FakeGenAiModels()))

    async def generate_structured_content(self, **kwargs: Any) -> Any:
        return await self.client.aio.models.generate_content(**kwargs)

    async def get_text_embedding(
        self, text: str, *, embedding_purpose: str = "document", return_cache_status: bool = False
    ) -> Any:
        del text, embedding_purpose
        embedding = _seed_embedding()
        return (embedding, True) if return_cache_status else embedding


def _fake_llm_agent(**kwargs: Any) -> FunctionNode:
    """Replace the external model call with a deterministic ADK node."""
    tools = {tool.__name__: tool for tool in kwargs["tools"]}

    async def coffee_turn(ctx: Any, node_input: str) -> types.Content:
        del ctx
        result = await tools["search_products_by_vector"](node_input, limit=5, similarity_threshold=0.5)
        products = result["products"]
        assert products, "product RAG must return at least one Oracle-backed match"
        return types.Content(
            role="model", parts=[types.Part(text=f"{products[0]['name']} is a good fit for a bold coffee request.")]
        )

    return FunctionNode(func=coffee_turn, name=str(kwargs["name"]), parameter_binding="state")


async def test_chat_workflow_populates_result_shape_with_oracle_backed_rag(
    monkeypatch: pytest.MonkeyPatch,
    driver: OracleAsyncDriver,
    unique_test_id: str,
    tracked_product_skus: Callable[[str], None],
) -> None:
    sku = f"CHAT-{unique_test_id}"
    tracked_product_skus(sku)
    await _seed_product_with_embedding(driver, sku)
    session_id = f"integration-chat-workflow-{uuid.uuid4().hex}"
    query = f"I need something that will wake me up {uuid.uuid4().hex}"

    from app.domain.chat.services import adk as adk_module

    monkeypatch.setattr(adk_module, "LlmAgent", _fake_llm_agent)
    configured = SimpleNamespace(
        ai=SimpleNamespace(project_id="test-project", api_key=None, chat_model="gemini-3.1-flash-lite"),
        chat=SimpleNamespace(
            session_app_name="coffee_assistant",
            response_cache_version="menu-grounded-v2",
            response_cache_ttl_minutes=60,
            product_search_limit=5,
            product_search_threshold=0.7,
            grounded_answer_timeout_seconds=2.5,
            display_history_limit=40,
        ),
    )
    monkeypatch.setattr(adk_module, "get_settings", lambda: configured)
    monkeypatch.setattr("app.domain.chat.services._adk_grounding.get_settings", lambda: configured)

    from app.config import db

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

    result: dict[str, Any] | None = None
    async for event in runner.stream_request(
        query=query, user_id="integration-user", session_id=session_id, persona="barista", tools_service=tools_service
    ):
        if event.get("type") == "final":
            result = event
    assert result is not None, "stream_request must emit a final event"

    assert set(result) == {
        "type",
        "answer",
        "session_id",
        "response_time_ms",
        "intent_detected",
        "search_metrics",
        "from_cache",
        "embedding_cache_hit",
        "sql_phases",
        "store_results",
        "inventory_results",
        "map_actions",
        "location_context",
    }
    assert result["type"] == "final"
    assert result["session_id"] == session_id
    assert result["intent_detected"] == IntentLabel.PRODUCT_RAG.value
    assert result["answer"]
    assert result["search_metrics"]["products_found"] >= 1
    assert result["search_metrics"]["results_count"] == result["search_metrics"]["products_found"]
    assert result["search_metrics"]["vector_query"] == query
    assert {"embedding_ms", "oracle_ms", "tool_ms"} <= result["search_metrics"].keys()
    assert result["response_time_ms"] < 4000
    assert result["from_cache"] is False
    assert result["embedding_cache_hit"] is True
    assert result["store_results"] == []
    assert result["inventory_results"] == []
    assert result["map_actions"] == []
    assert result["location_context"] == {}
    sql_keys = {phase["sql_key"] for phase in result["sql_phases"]}
    assert {"get-cached-response", "get-cached-embedding", "vector-search-products"} <= sql_keys
    vector_phase = next(phase for phase in result["sql_phases"] if phase["sql_key"] == "vector-search-products")
    assert vector_phase["row_count"] >= 1
    assert vector_phase["binds"]["query_vector"].startswith("<VECTOR[3072 FLOAT32], sha256=")
    assert classifier.phrases == [query]

    persisted = await session_service.get_session(
        app_name="coffee_assistant", user_id="integration-user", session_id=session_id
    )
    assert persisted is not None
    assert persisted.state["intent"] == IntentLabel.PRODUCT_RAG.value

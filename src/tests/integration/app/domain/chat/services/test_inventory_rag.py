# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ADK chat inventory-aware RAG integration tests."""

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
    return [0.5] * 3072


async def _seed_product_with_inventory(
    driver: OracleAsyncDriver, sku: str, store_id: int, qty: int, status: str
) -> int:
    """Insert a uniquely keyed product and inventory row for testing."""
    await driver.execute(
        """
        INSERT INTO product (name, description, price, category, sku, in_stock, embedding)
        VALUES (:name, :description, :price, :category, :sku, TRUE, :embedding)
        """,
        name=f"Inventory Test Roast {sku}",
        description="Bold coffee seeded for inventory RAG tests",
        price=12.99,
        category="Coffee",
        sku=sku,
        embedding=_seed_embedding(),
    )
    await driver.commit()

    rows = await driver.select("SELECT id FROM product WHERE sku = :sku", sku=sku)
    product_id = int(rows[0]["id"])

    await driver.execute(
        """
        INSERT INTO store_product_inventory (store_id, product_id, quantity_available, stock_status, pickup_available)
        VALUES (:store_id, :product_id, :qty, :status, TRUE)
        """,
        store_id=store_id,
        product_id=product_id,
        qty=qty,
        status=status,
    )
    await driver.commit()
    return product_id


async def _dallas_store(driver: OracleAsyncDriver) -> tuple[int, str]:
    """Return the seeded Dallas store used by inventory RAG fixtures."""
    stores = await driver.select("SELECT id, name FROM store WHERE name LIKE '%Dallas%'")
    assert stores, "Dallas store must be seeded in database"
    return int(stores[0]["id"]), str(stores[0]["name"])


class FakeIntentClassifier:
    async def classify(self, phrase: str) -> IntentLabel:
        return IntentLabel.PRODUCT_RAG


class _FakeGenAiModels:
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
    tools = {tool.__name__: tool for tool in kwargs["tools"]}

    async def coffee_turn(ctx: Any, node_input: str) -> types.Content:
        del ctx
        result = await tools["search_products_by_vector"](node_input, limit=5, similarity_threshold=0.5)
        products = result["products"]
        assert products, "product RAG must return at least one Oracle-backed match"
        return types.Content(role="model", parts=[types.Part(text=f"Selected {products[0]['name']}")])

    return FunctionNode(func=coffee_turn, name=str(kwargs["name"]), parameter_binding="state")


def _chat_settings() -> SimpleNamespace:
    """Return deterministic settings for the inventory RAG integration path."""
    return SimpleNamespace(
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


def _tools_service(driver: OracleAsyncDriver) -> AgentToolsService:
    """Build the request-scoped tool service with deterministic Vertex behavior."""
    return AgentToolsService(
        driver=driver,
        product_service=ProductService(driver),
        metrics_service=MetricsService(driver),
        vertex_ai_service=FakeVertexAIService(),  # type: ignore[arg-type]
        store_service=StoreService(driver),
        cache_service=CacheService(driver),
    )


async def test_inventory_aware_rag_recommends_and_annotates(
    monkeypatch: pytest.MonkeyPatch,
    driver: OracleAsyncDriver,
    unique_test_id: str,
    tracked_product_skus: Callable[[str], None],
) -> None:
    # 1. Resolve a valid store (e.g. Dallas store from fixtures, ID is usually 1)
    dallas_store_id, dallas_store_name = await _dallas_store(driver)

    # 2. Seed product + inventory at Dallas store (IN_STOCK)
    sku = f"RAG-INV-{unique_test_id}"
    tracked_product_skus(sku)
    product_id = await _seed_product_with_inventory(driver, sku, dallas_store_id, qty=42, status="IN_STOCK")

    # 3. Setup mock configs
    from app.domain.chat.services import adk as adk_module

    monkeypatch.setattr(adk_module, "LlmAgent", _fake_llm_agent)
    configured = _chat_settings()
    monkeypatch.setattr(adk_module, "get_settings", lambda: configured)
    monkeypatch.setattr("app.domain.chat.services._adk_grounding.get_settings", lambda: configured)

    from app.config import db

    store = OracleAsyncADKStore(config=db)
    await store.ensure_tables()
    session_service = SQLSpecSessionService(store)
    runner = ADKRunner(
        session_service=session_service,
        classifier=FakeIntentClassifier(),  # type: ignore[arg-type]
        persona_manager=PersonaManager(),
    )
    tools_service = _tools_service(driver)

    # 4. Request with location context targeting Dallas
    session_id = f"integration-rag-inv-{uuid.uuid4().hex}"

    result: dict[str, Any] | None = None
    async for event in runner.stream_request(
        query="Give me something bold",
        user_id="integration-user",
        session_id=session_id,
        persona="enthusiast",
        tools_service=tools_service,
        location_context={"store_name": dallas_store_name},
    ):
        if event.get("type") == "final":
            result = event
    assert result is not None

    # 5. Assertions
    assert result["intent_detected"] == "PRODUCT_RAG"
    # The answer should contain the product name and stock information from grounding
    assert f"Inventory Test Roast {sku}" in result["answer"]
    assert f"At {dallas_store_name}, this is in stock with 42 on hand" in result["answer"]

    # Verify inventory results payload
    assert len(result["inventory_results"]) >= 1
    inv_item = result["inventory_results"][0]
    assert inv_item["id"] == product_id
    assert inv_item["storeId"] == dallas_store_id
    assert inv_item["stockStatus"] == "IN_STOCK"
    assert inv_item["quantityAvailable"] == 42

    # Verify sql phases
    sql_keys = [phase["sql_key"] for phase in result["sql_phases"]]
    assert "vector-search-products-by-store" in sql_keys
    assert "vector-search-products" not in sql_keys

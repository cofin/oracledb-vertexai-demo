# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin the make_workflow factory shape and the parallel fan-out body."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk import Workflow
from google.adk.workflow._function_node import FunctionNode

from app.domain.chat.services.classifier import IntentLabel
from app.domain.chat.services.workflow import (
    make_coffee_node,
    make_intent_node,
    make_workflow,
)


def test_make_intent_node_binds_node_input_with_classifier() -> None:
    classifier = MagicMock()
    intent = make_intent_node(classifier)

    assert isinstance(intent, FunctionNode)
    assert intent.name == "intent"
    assert intent.parameter_binding == "node_input"


def test_make_coffee_node_binds_node_input_with_agent() -> None:
    agent = MagicMock()
    coffee = make_coffee_node(agent)

    assert isinstance(coffee, FunctionNode)
    assert coffee.name == "coffee_turn"
    assert coffee.parameter_binding == "node_input"


def test_make_workflow_returns_named_workflow_with_single_start_edge() -> None:
    classifier = MagicMock()
    agent = MagicMock()
    workflow = make_workflow(classifier, agent)

    assert isinstance(workflow, Workflow)
    assert workflow.name == "coffee_workflow"
    assert len(workflow.edges) == 1
    src, dst = workflow.edges[0]
    assert src == "START"
    assert isinstance(dst, FunctionNode)
    assert dst.name == "classify_and_respond"


@pytest.mark.asyncio
async def test_intent_node_func_returns_classifier_label_value() -> None:
    classifier = MagicMock()
    classifier.classify = AsyncMock(return_value=IntentLabel.PRODUCT_RAG)
    intent = make_intent_node(classifier)

    result = await intent._func(ctx=MagicMock(), user_query="dark roast")

    classifier.classify.assert_awaited_once_with("dark roast")
    assert result == "PRODUCT_RAG"


@pytest.mark.asyncio
async def test_coffee_node_func_delegates_to_ctx_run_node_with_agent() -> None:
    agent = MagicMock()
    coffee = make_coffee_node(agent)
    ctx = MagicMock()
    ctx.run_node = AsyncMock(return_value="brewed answer")

    result = await coffee._func(ctx=ctx, user_query="best beans")

    ctx.run_node.assert_awaited_once_with(agent, "best beans")
    assert result == "brewed answer"


@pytest.mark.asyncio
async def test_classify_and_respond_func_runs_intent_and_coffee_in_parallel() -> None:
    classifier = MagicMock()
    agent = MagicMock()
    workflow = make_workflow(classifier, agent)
    classify_and_respond = workflow.edges[0][1]

    ctx = MagicMock()

    async def _stub_run(passed_node, value):
        if passed_node.name == "intent":
            return "PRODUCT_RAG"
        return f"answer-for:{value}"

    ctx.run_node = AsyncMock(side_effect=_stub_run)

    result = await classify_and_respond._func(ctx=ctx, user_query="latte")

    assert result == {"intent": "PRODUCT_RAG", "answer": "answer-for:latte"}
    assert ctx.run_node.await_count == 2

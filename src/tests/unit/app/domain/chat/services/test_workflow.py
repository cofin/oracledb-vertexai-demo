# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin the make_workflow factory shape and the parallel fan-out body."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk import Workflow
from google.adk.workflow import JoinNode
from google.adk.workflow._function_node import FunctionNode

from app.domain.chat.services.classifier import IntentLabel
from app.domain.chat.services.workflow import (
    make_coffee_node,
    make_intent_node,
    make_workflow,
)


def _coffee_node(node_input: str) -> str:
    return f"answer:{node_input}"


def test_make_intent_node_binds_node_input_with_classifier() -> None:
    classifier = MagicMock()
    intent = make_intent_node(classifier)

    assert isinstance(intent, FunctionNode)
    assert intent.name == "intent"
    assert intent.parameter_binding == "state"


def test_make_coffee_node_binds_node_input_with_agent() -> None:
    copied = MagicMock()
    copied.name = "coffee_turn"
    agent = MagicMock()
    agent.model_copy.return_value = copied
    coffee = make_coffee_node(agent)

    assert coffee.name == "coffee_turn"
    agent.model_copy.assert_called_once_with(update={"name": "coffee_turn"})


def test_make_workflow_returns_named_workflow_with_joined_parallel_edges() -> None:
    classifier = MagicMock()
    agent = MagicMock()
    agent.model_copy.return_value = FunctionNode(func=_coffee_node, name="coffee_turn")
    workflow = make_workflow(classifier, agent)

    assert isinstance(workflow, Workflow)
    assert workflow.name == "coffee_workflow"
    assert workflow.max_concurrency == 2
    assert len(workflow.edges) == 3
    assert workflow.edges[0][0] == "START"
    assert isinstance(workflow.edges[0][1], FunctionNode)
    assert isinstance(workflow.edges[0][2], JoinNode)
    assert workflow.edges[1][0] == "START"
    assert workflow.edges[1][1].name == "coffee_turn"
    assert isinstance(workflow.edges[1][2], JoinNode)
    assert isinstance(workflow.edges[2][0], JoinNode)
    assert isinstance(workflow.edges[2][1], FunctionNode)
    assert workflow.edges[2][1].name == "classify_and_respond"


@pytest.mark.asyncio
async def test_intent_node_func_returns_classifier_label_value() -> None:
    classifier = MagicMock()
    classifier.classify = AsyncMock(return_value=IntentLabel.PRODUCT_RAG)
    intent = make_intent_node(classifier)

    result = await intent._func(ctx=MagicMock(), node_input="dark roast")

    classifier.classify.assert_awaited_once_with("dark roast")
    assert result == "PRODUCT_RAG"


def test_classify_and_respond_func_merges_join_outputs() -> None:
    classifier = MagicMock()
    agent = MagicMock()
    agent.model_copy.return_value = FunctionNode(func=_coffee_node, name="coffee_turn")
    workflow = make_workflow(classifier, agent)
    classify_and_respond = workflow.edges[2][1]
    ctx = MagicMock()
    ctx.state = {}

    result = classify_and_respond._func(
        ctx=ctx,
        node_input={"intent": "PRODUCT_RAG", "coffee_turn": "answer-for:latte"},
    )

    assert result == {"intent": "PRODUCT_RAG", "answer": "answer-for:latte"}
    assert ctx.state["intent"] == "PRODUCT_RAG"

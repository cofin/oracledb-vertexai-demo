# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow factory wiring intent classification and coffee response in parallel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from google.adk import Context, Workflow
from google.adk.workflow import JoinNode
from google.adk.workflow._function_node import FunctionNode
from google.genai import types

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

    from app.domain.chat.services.classifier import FlashLiteIntentClassifier


def make_intent_node(classifier: FlashLiteIntentClassifier) -> FunctionNode:
    """Build a node that classifies the input string to an intent label.

    Returns:
        Function node for intent classification.
    """

    async def intent_node(ctx: Context, node_input: str) -> str:
        label = await classifier.classify(node_input)
        return label.value

    return FunctionNode(func=intent_node, name="intent", parameter_binding="state")


def make_coffee_node(agent: LlmAgent) -> LlmAgent:
    """Build the LLM node used by the graph fan-out.

    Returns:
        A copied agent node named for join output collection.
    """
    if hasattr(agent, "model_copy"):
        return agent.model_copy(update={"name": "coffee_turn"})
    agent.name = "coffee_turn"
    return agent


def _content_to_text(value: Any) -> str:
    """Convert ADK node outputs into displayable model text.

    Returns:
        Text extracted from ADK content, mappings, or primitive values.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, types.Content):
        return "".join(part.text or "" for part in value.parts or [])
    if isinstance(value, dict):
        answer = value.get("answer") or value.get("text") or value.get("message")
        return _content_to_text(answer)
    return str(value)


def make_workflow(classifier: FlashLiteIntentClassifier, agent: LlmAgent) -> Workflow:
    """Build the coffee workflow with parallel intent + agent fan-out.

    Returns:
        Static ADK workflow graph for one chat turn.
    """
    intent = make_intent_node(classifier)
    coffee = make_coffee_node(agent)
    join = JoinNode(name="join")

    def classify_and_respond(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        intent_label = str(node_input.get("intent") or "GENERAL_CONVERSATION")
        answer = _content_to_text(node_input.get("coffee_turn"))
        ctx.state["intent"] = intent_label
        return {"answer": answer, "intent": intent_label}

    merge = FunctionNode(func=classify_and_respond, name="classify_and_respond", rerun_on_resume=True)
    # docs:start-workflow-fanout
    return Workflow(
        name="coffee_workflow",
        edges=[
            ("START", intent, join),
            ("START", coffee, join),
            (join, merge),
        ],
        max_concurrency=2,
    )
    # docs:end-workflow-fanout


__all__ = ("make_coffee_node", "make_intent_node", "make_workflow")

# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow factory wiring intent classification and coffee response in parallel."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from google.adk import Context, Workflow
from google.adk.workflow._function_node import FunctionNode

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

    from app.domain.chat.services.classifier import FlashLiteIntentClassifier


def make_intent_node(classifier: FlashLiteIntentClassifier) -> FunctionNode:
    """Build a node that classifies ``user_query`` to an intent label string."""

    async def intent_node(ctx: Context, user_query: str) -> str:
        label = await classifier.classify(user_query)
        return label.value

    return FunctionNode(func=intent_node, name="intent", parameter_binding="node_input")


def make_coffee_node(agent: LlmAgent) -> FunctionNode:
    """Build a node that runs ``agent`` against ``user_query`` via the workflow context."""

    async def coffee_turn(ctx: Context, user_query: str) -> str:
        return await ctx.run_node(agent, user_query)

    return FunctionNode(func=coffee_turn, name="coffee_turn", parameter_binding="node_input")


def make_workflow(classifier: FlashLiteIntentClassifier, agent: LlmAgent) -> Workflow:
    """Build the coffee workflow with parallel intent + agent fan-out."""
    intent = make_intent_node(classifier)
    coffee = make_coffee_node(agent)

    async def classify_and_respond(ctx: Context, user_query: str) -> dict[str, Any]:
        intent_label, answer = await asyncio.gather(
            ctx.run_node(intent, user_query),
            ctx.run_node(coffee, user_query),
        )
        return {"answer": answer, "intent": intent_label}

    fan_out = FunctionNode(
        func=classify_and_respond, name="classify_and_respond", parameter_binding="node_input"
    )
    return Workflow(name="coffee_workflow", edges=[("START", fan_out)])


__all__ = ("make_coffee_node", "make_intent_node", "make_workflow")

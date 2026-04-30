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
    """Build a node that classifies the input string to an intent label."""

    async def intent_node(ctx: Context, node_input: str) -> str:
        label = await classifier.classify(node_input)
        return label.value

    return FunctionNode(func=intent_node, name="intent")


def make_coffee_node(agent: LlmAgent) -> FunctionNode:
    """Build a node that runs ``agent`` against the input string via the workflow context."""

    async def coffee_turn(ctx: Context, node_input: str) -> str:
        return await ctx.run_node(agent, node_input)

    return FunctionNode(func=coffee_turn, name="coffee_turn", rerun_on_resume=True)


def make_workflow(classifier: FlashLiteIntentClassifier, agent: LlmAgent) -> Workflow:
    """Build the coffee workflow with parallel intent + agent fan-out."""
    intent = make_intent_node(classifier)
    coffee = make_coffee_node(agent)

    async def classify_and_respond(ctx: Context, node_input: str) -> dict[str, Any]:
        intent_label, answer = await asyncio.gather(
            ctx.run_node(intent, node_input),
            ctx.run_node(coffee, node_input),
        )
        return {"answer": answer, "intent": intent_label}

    fan_out = FunctionNode(
        func=classify_and_respond, name="classify_and_respond", rerun_on_resume=True
    )
    return Workflow(name="coffee_workflow", edges=[("START", fan_out)])


__all__ = ("make_coffee_node", "make_intent_node", "make_workflow")

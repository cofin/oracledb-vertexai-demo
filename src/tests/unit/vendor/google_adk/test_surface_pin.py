# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin the google-adk 2.0b1 surface that the ADK 2.0 runner depends on."""

from __future__ import annotations

import inspect


def test_top_level_imports() -> None:
    from google.adk import Context, Runner, Workflow

    assert all(callable(c) or inspect.isclass(c) for c in (Context, Runner, Workflow))


def test_workflow_module_imports() -> None:
    from google.adk.workflow import BaseNode, FunctionNode, node

    assert inspect.isclass(BaseNode)
    assert inspect.isclass(FunctionNode)
    assert callable(node)


def test_agent_imports() -> None:
    from google.adk.agents import LlmAgent
    from google.adk.agents.callback_context import CallbackContext

    assert inspect.isclass(LlmAgent)
    assert inspect.isclass(CallbackContext)


def test_runner_accepts_workflow_via_node_kwarg() -> None:
    from google.adk import Runner

    params = inspect.signature(Runner.__init__).parameters
    assert "node" in params, "Runner must expose `node=` for Workflow/BaseNode roots"
    assert "agent" in params, "Runner must still expose `agent=` for BaseAgent entry points"
    assert "session_service" in params, "Runner must accept session_service"


def test_workflow_is_basenode_not_baseagent() -> None:
    from google.adk import Workflow
    from google.adk.agents import BaseAgent
    from google.adk.workflow import BaseNode

    assert issubclass(Workflow, BaseNode), "Workflow must inherit from BaseNode (Runner.node= path)"
    assert not issubclass(Workflow, BaseAgent), "Workflow must NOT inherit from BaseAgent"


def test_node_decorator_keyword_surface() -> None:
    from google.adk.workflow import node

    params = inspect.signature(node).parameters
    for kw in ("name", "rerun_on_resume", "retry_config", "timeout", "parallel_worker"):
        assert kw in params, f"@node decorator must expose `{kw}=`"


def test_node_decorator_produces_function_node() -> None:
    from google.adk.workflow import BaseNode, FunctionNode, node

    @node(name="probe")
    async def _probe(ctx, query: str) -> str:
        return query

    assert isinstance(_probe, FunctionNode)
    assert isinstance(_probe, BaseNode)


def test_context_run_node_signature() -> None:
    from google.adk import Context

    params = inspect.signature(Context.run_node).parameters
    assert "node" in params, "Context.run_node must accept positional `node`"
    assert "node_input" in params, "Context.run_node must accept `node_input`"


def test_genai_types_for_classifier() -> None:
    from google.genai import types

    cfg = types.GenerateContentConfig(
        response_mime_type="text/x.enum",
        response_schema={"type": "STRING", "enum": ["A", "B"]},
        system_instruction="x",
    )
    assert cfg.response_mime_type == "text/x.enum"
    assert cfg.response_schema == {"type": "STRING", "enum": ["A", "B"]}

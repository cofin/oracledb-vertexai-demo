---
type: Task
id: task-5
flow_id: native-agentic-runtime
state: closed
title: Implement A2A 1.0 Agent Protocol with AgentCard Discovery and CoffeeAgentExecutor
description: Add litestar-mcp[a2a], define AgentCard discovery at /.well-known/agent-card.json, implement CoffeeAgentExecutor, and mount LitestarA2A on /a2a.
verification_strategy: behavior_tdd
depends_on:
  - task-1
  - task-3
commit: null
tags:
  - task
  - a2a
  - agent-card
  - json-rpc
  - litestar-a2a
---

# Task task-5: Implement A2A 1.0 Agent Protocol with AgentCard Discovery and CoffeeAgentExecutor

## Objective
Enable Agent-to-Agent (A2A 1.0) protocol communication in Cymbal Coffee using `litestar-mcp[a2a]` (`a2a-sdk`), exposing public agent card discovery at `GET /.well-known/agent-card.json` and streaming JSON-RPC task execution at `POST /a2a`.

## Itemized Checklist
- [x] Add `"litestar-mcp[a2a]"` to `dependencies` in `pyproject.toml` and run `uv sync`.
- [x] Implement `src/app/domain/ai/a2a/card.py` declaring `COFFEE_AGENT_CARD`.
- [x] Implement `src/app/domain/ai/a2a/executor.py` declaring `CoffeeAgentExecutor(AgentExecutor)` with Dishka request-scoped container resolution.
- [x] Mount `LitestarA2A` in `src/app/server/plugins.py` using `A2AConfig(path="/a2a", agent_card_path="/.well-known/agent-card.json")`.
- [x] Author test suite `src/tests/unit/app/domain/ai/a2a/test_a2a.py` verifying `GET /.well-known/agent-card.json` discovery and `POST /a2a` task execution.

## Implementation Details & Code Samples

### 1. `pyproject.toml`
```toml
dependencies = [
    "litestar[cryptography,jinja,jwt,opentelemetry,structlog]",
    "litestar-granian[uvloop]",
    "litestar-mcp[a2a]>=0.14.0",
    "sqlspec[mypyc,oracledb,performance]",
    "numpy",
    "python-dotenv",
    "dishka",
    "litestar-vite",
    "litestar-autowire[dishka]>=0.2.0",
    "litestar-htmx>=0.5.0",
    "litestar-security>=0.6.0",
]
```

### 2. `src/app/domain/ai/a2a/card.py`
```python
"""AgentCard declaration for A2A 1.0 discovery."""

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

COFFEE_AGENT_CARD = AgentCard(
    name="Cymbal Coffee Barista Agent",
    description="Intelligent agent for specialty coffee recommendations, brew recipes, and store inventory.",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=True),
    skills=[
        AgentSkill(
            id="coffee_recommendation",
            name="Coffee Recommendations",
            description="Recommends roasts and beverages grounded in the Cymbal Coffee catalog.",
            tags=["coffee", "recommendation"],
        ),
        AgentSkill(
            id="store_inventory",
            name="Store Inventory & Pickup",
            description="Checks product availability and store hours across Dallas-Fort Worth locations.",
            tags=["inventory", "stores"],
        ),
    ],
    supported_interfaces=[
        AgentInterface(
            url="http://localhost:8000/a2a",
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        )
    ],
)
```

### 3. `src/app/domain/ai/a2a/executor.py`
```python
"""A2A AgentExecutor implementation delegating to AgentOrchestrationService."""

from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, TextPart
from dishka import AsyncContainer, Scope

from app.domain.ai.services.agent_service import AgentOrchestrationService


class CoffeeAgentExecutor(AgentExecutor):
    """Executes incoming A2A turns within a request-scoped Dishka container."""

    def __init__(self, container: AsyncContainer) -> None:
        self._container = container

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Process an incoming A2A message and push responses to event_queue."""
        user_text = ""
        if context.message and context.message.parts:
            for part in context.message.parts:
                if isinstance(part, TextPart) and part.text:
                    user_text += part.text

        session_id = context.context_id or "a2a-default-session"
        user_id = context.client_id or "a2a-client"

        async with self._container(scope=Scope.REQUEST) as req_container:
            orchestrator = await req_container.get(AgentOrchestrationService)
            accumulated_answer: list[str] = []

            async for frame in orchestrator.stream_conversation_turn(
                session_id=session_id,
                user_id=user_id,
                message=user_text,
            ):
                if frame.get("type") == "delta":
                    delta_text = str(frame.get("text", ""))
                    accumulated_answer.append(delta_text)

            complete_message = Message(
                role="agent",
                parts=[TextPart(text="".join(accumulated_answer))],
            )
            await event_queue.put(complete_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel an in-flight A2A task."""
```

### 4. `src/app/server/plugins.py`
```python
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from litestar_mcp import A2AConfig as _A2AConfig
from litestar_mcp import LitestarA2A as _LitestarA2A

from app.domain.ai.a2a.card import COFFEE_AGENT_CARD
from app.domain.ai.a2a.executor import CoffeeAgentExecutor

# In _initialize():
# Note: CoffeeAgentExecutor is initialized with the root Dishka container.
# LitestarA2A mounts POST /a2a and GET /.well-known/agent-card.json
```

### 5. `src/tests/unit/app/domain/ai/a2a/test_a2a.py`
```python
"""Unit tests for A2A 1.0 protocol endpoints."""

import pytest
from litestar.testing import AsyncTestClient

from app.server.asgi import create_app


@pytest.mark.anyio
async def test_agent_card_discovery() -> None:
    """Verify GET /.well-known/agent-card.json returns valid card metadata."""
    app = create_app()
    async with AsyncTestClient(app=app) as client:
        res = await client.get("/.well-known/agent-card.json")
        assert res.status_code == 200
        card = res.json()
        assert card["name"] == "Cymbal Coffee Barista Agent"
        assert card["version"] == "1.0.0"
        assert len(card["skills"]) >= 2
```

## Verification
- Strategy: `behavior_tdd`
- Initial Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/a2a/test_a2a.py`
  - Expected: Fails because A2A test file does not exist.
- Final Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/a2a/test_a2a.py && make lint`
  - Expected: Agent card discovery succeeds with valid JSON and ETag; `make lint` clean.

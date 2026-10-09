---
type: Task
id: task-4
flow_id: litestar-mcp-agent-adoption
state: open
title: Adopt Upstream AgentStreamFrame and Refactor Chat Controller
description: Replace custom AgentStreamService with litestar_mcp.AgentStreamFrame, refactor CoffeeChatController, and delete hand-rolled _stream.py and _types.py.
verification_strategy: behavior_tdd
depends_on:
  - task-3
commit: null
tags:
  - task
  - streaming
  - sse
  - chat-controller
---

# Task task-4: Adopt Upstream AgentStreamFrame and Refactor Chat Controller

## Objective
Migrate SSE streaming in `CoffeeChatController` and `AgentOrchestrationService` to upstream's typed `AgentStreamFrame` (`session`, `delta`, `thought`, `tool_call`, `tool_result`, `complete`, `error`), deleting the custom SSE queue drainer `src/app/domain/ai/runtime/_stream.py` and custom wire types `src/app/domain/ai/runtime/_types.py`.

## Itemized Checklist
- [ ] Update `src/app/domain/ai/services/agent_service.py`:
  - Import `AgentStreamFrame` and `TurnRequest` from `litestar_mcp.agent`.
  - Update `stream_conversation_turn` to yield `AgentStreamFrame` directly from `runtime.stream_turn(req)`.
- [ ] Refactor `src/app/domain/chat/controllers/_chat.py`:
  - Update `CoffeeChatController.stream_chat`:
    ```python
    @post("/stream")
    async def stream_chat(
        self,
        request: Request[Any, Any, Any],
        data: ChatPrompt,
        orchestrator: Inject[AgentOrchestrationService],
    ) -> ServerSentEvent:
        """Stream an agent turn yielding standardized AgentStreamFrame SSE messages."""
        async def _generator() -> AsyncIterator[ServerSentEventMessage]:
            async for frame in orchestrator.stream_conversation_turn(...):
                yield frame.to_sse_message()

        return ServerSentEvent(_generator())
    ```
- [ ] Delete hand-rolled streaming and wire struct files:
  - `src/app/domain/ai/runtime/_stream.py`
  - `src/app/domain/ai/runtime/_types.py`
- [ ] Update `src/app/domain/ai/runtime/__init__.py` to re-export upstream `AgentStreamFrame` and `iter_agent_stream`.
- [ ] Update integration tests in `src/tests/integration/app/domain/chat/controllers/test_chat_http.py` to assert against `AgentStreamFrame` event messages.
- [ ] Run targeted verification (`uv run pytest src/tests/integration/app/domain/chat/controllers/test_chat_http.py` and `make lint`).

## Verification
- Strategy: `behavior_tdd`
- Initial Evidence: Run `uv run pytest src/tests/integration/app/domain/chat/controllers/test_chat_http.py -k test_stream_returns_agent_stream_frame`
  - Expected: Fails because `AgentStreamFrame` is not yet yielded by the controller.
- Final Evidence: Run `uv run pytest src/tests/integration/app/domain/chat/controllers/test_chat_http.py && make lint`
  - Expected: All HTTP streaming tests pass cleanly with standard SSE frames.

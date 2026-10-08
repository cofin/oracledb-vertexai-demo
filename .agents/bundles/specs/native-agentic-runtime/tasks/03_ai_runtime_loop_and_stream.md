---
type: Task
id: task-3
flow_id: native-agentic-runtime
state: closed
title: Implement AgentRuntime Re-entrant Execution Loop, SSE Stream Adapter, and AgentOrchestrationService
description: Build AgentRuntime execution loop with tool dispatching, terminal-aware AgentStreamService with keep-alive pings, and AgentOrchestrationService in app.domain.ai.
verification_strategy: behavior_tdd
depends_on:
  - task-1
  - task-2
commit: null
tags:
  - task
  - agent-loop
  - sse-streaming
  - stream-service
  - orchestration
---

# Task task-3: Implement AgentRuntime Re-entrant Execution Loop, SSE Stream Adapter, and AgentOrchestrationService

## Objective
Implement the re-entrant agent execution loop, parallel tool dispatch cycle, terminal-aware Server-Sent Events (SSE) adapter with keep-alive pings, and the high-level `AgentOrchestrationService` in `src/app/domain/ai/`.

## Itemized Checklist
- [x] Implement `src/app/domain/ai/runtime/_loop.py` with `AgentRuntime`.
- [x] Implement `src/app/domain/ai/runtime/_stream.py` with `AgentStreamService` and `build_tool_preview()`.
- [x] Implement `src/app/domain/ai/services/agent_service.py` with `AgentOrchestrationService`.
- [x] Export public runtime loop and stream services in `src/app/domain/ai/runtime/__init__.py`.
- [x] Author test suite `src/tests/unit/app/domain/ai/runtime/test_loop_stream.py` validating tool recursion, turn limits, keep-alive ping timeouts, and terminal frame guarantees.

## Implementation Details & Code Samples

### 1. `src/app/domain/ai/runtime/_loop.py`
```python
"""Re-entrant agent execution loop with dynamic tool dispatching."""

from collections.abc import AsyncIterator
from typing import Any

from app.domain.ai.runtime._context import CallContext
from app.domain.ai.runtime._model import GeminiModelClient
from app.domain.ai.runtime._spec import SpecTree, fence_context_block
from app.domain.ai.runtime._tools import Tool, ToolDeclaration, execute_parallel
from app.domain.ai.runtime._types import (
    AgentEvent,
    AgentLimits,
    Content,
    FunctionCall,
    FunctionResponse,
    Part,
)


class AgentRuntime:
    """Core re-entrant agent execution loop."""

    def __init__(
        self,
        model_client: GeminiModelClient,
        limits: AgentLimits = AgentLimits(),
    ) -> None:
        self._model_client = model_client
        self._limits = limits

    async def execute_turn(
        self,
        *,
        spec_tree: SpecTree,
        session_id: str,
        invocation_id: str,
        user_message: str,
        ctx: CallContext,
        history: list[AgentEvent] | None = None,
        dynamic_context: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Execute one re-entrant conversation turn until completion or budget exhaustion."""
        current_spec = spec_tree.root
        history_events = list(history or [])
        contents: list[Content] = [ev.content for ev in history_events if ev.content]

        user_text = user_message
        if dynamic_context:
            fenced = fence_context_block("ACTIVE_SESSION_CONTEXT", dynamic_context)
            user_text = f"{user_message}\n\n{fenced}"

        contents.append(Content(role="user", parts=[Part(text=user_text)]))

        model_calls = 0
        tool_calls_count = 0

        while model_calls < self._limits.max_model_calls_per_turn:
            model_calls += 1
            tools_map: dict[str, Tool] = {t.name: t for t in current_spec.tools}
            tool_decls: list[ToolDeclaration] = [t.declaration() for t in current_spec.tools]

            collected_parts: list[Part] = []
            pending_calls: list[FunctionCall] = []

            async for event in self._model_client.generate_stream(
                contents,
                tools=tool_decls,
                system_instruction=current_spec.static_instruction,
                model=current_spec.model,
            ):
                event.session_id = session_id
                event.invocation_id = invocation_id
                event.turn = ctx.turn
                event.agent = current_spec.name
                yield event

                if event.content and event.content.parts:
                    for p in event.content.parts:
                        if p.function_call:
                            pending_calls.append(p.function_call)
                        elif p.text:
                            collected_parts.append(p)

            if not pending_calls:
                break

            tool_calls_count += len(pending_calls)
            if tool_calls_count > self._limits.max_tool_calls_per_turn:
                yield AgentEvent(
                    session_id=session_id,
                    invocation_id=invocation_id,
                    agent=current_spec.name,
                    finish_reason="TOOL_LIMIT_EXCEEDED",
                    content=Content(role="model", parts=[Part(text="Tool execution limit reached for this turn.")]),
                )
                break

            responses: list[FunctionResponse] = await execute_parallel(pending_calls, tools_map, ctx)

            for resp in responses:
                if resp.name == "transfer_to_agent":
                    target_name = str(resp.response.get("transferred_to", ""))
                    if target_name and target_name in spec_tree.specialists:
                        current_spec = spec_tree.specialists[target_name]

            response_parts = [Part(function_response=r) for r in responses]
            contents.append(Content(role="model", parts=[Part(function_call=c) for c in pending_calls]))
            contents.append(Content(role="user", parts=response_parts))

            yield AgentEvent(
                session_id=session_id,
                invocation_id=invocation_id,
                agent=current_spec.name,
                content=Content(role="user", parts=response_parts),
            )
```

### 2. `src/app/domain/ai/runtime/_stream.py`
```python
"""Terminal-aware Server-Sent Events (SSE) adapter with keep-alive pings."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

import msgspec

from app.domain.ai.runtime._types import AgentEvent

DEFAULT_PING_INTERVAL = 5.0
RESULT_PREVIEW_CHARS = 240


def build_tool_preview(response: dict[str, Any], max_chars: int = RESULT_PREVIEW_CHARS) -> tuple[str, str]:
    """Return status classification and bounded string preview for tool results."""
    status = "error" if response.get("error") else "completed"
    encoded = msgspec.json.encode(response).decode("utf-8")
    if len(encoded) <= max_chars:
        return status, encoded
    return status, f"{encoded[: max_chars - 1]}…"


class AgentStreamService:
    """Adapts raw AgentEvents into an SSE-ready dictionary stream."""

    def __init__(self, ping_interval: float = DEFAULT_PING_INTERVAL) -> None:
        self._ping_interval = ping_interval

    async def _producer(
        self,
        source: AsyncIterator[AgentEvent],
        queue: asyncio.Queue[AgentEvent | Exception | None],
        fetch_next: asyncio.Event,
    ) -> None:
        try:
            while True:
                await fetch_next.wait()
                fetch_next.clear()
                try:
                    item = await anext(source)
                except StopAsyncIteration:
                    await queue.put(None)
                    break
                await queue.put(item)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            await queue.put(exc)

    async def adapt(
        self,
        event_stream: AsyncIterator[AgentEvent],
        session_id: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Yield structured SSE event frames with keep-alive pings and guaranteed cleanup."""
        fetch_next = asyncio.Event()
        fetch_next.set()
        queue: asyncio.Queue[AgentEvent | Exception | None] = asyncio.Queue(maxsize=1)
        producer_task = asyncio.create_task(self._producer(event_stream, queue, fetch_next))

        seen_calls: set[str] = set()
        has_final = False
        usage_total = {"prompt_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cached_tokens": 0}

        try:
            yield {"type": "session", "session_id": session_id}

            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=self._ping_interval)
                except TimeoutError:
                    if not has_final:
                        yield {"type": "ping"}
                    continue

                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item

                if item.usage:
                    usage_total["prompt_tokens"] += item.usage.prompt_tokens
                    usage_total["output_tokens"] += item.usage.output_tokens
                    usage_total["total_tokens"] += item.usage.total_tokens
                    usage_total["cached_tokens"] += item.usage.cached_tokens

                for call in item.function_calls():
                    call_key = call.id or call.name
                    if call_key not in seen_calls:
                        seen_calls.add(call_key)
                        yield {
                            "type": "tool_call",
                            "id": call.id,
                            "name": call.name,
                            "author": item.agent,
                            "args": call.args,
                        }

                for resp in item.function_responses():
                    status, preview = build_tool_preview(resp.response)
                    yield {
                        "type": "tool_end",
                        "id": resp.id,
                        "name": resp.name,
                        "author": item.agent,
                        "status": status,
                        "result_preview": preview,
                    }

                text_chunk = item.text()
                if text_chunk and item.agent != "user":
                    yield {"type": "delta", "text": text_chunk}

                if not item.partial and item.content and item.content.role == "model" and not item.function_calls():
                    has_final = True

                fetch_next.set()

            if has_final:
                yield {
                    "type": "final",
                    "session_id": session_id,
                    "search_metrics": usage_total,
                }
            else:
                yield {
                    "type": "error",
                    "code": "stream_incomplete",
                    "message": "Stream completed without final model turn.",
                }
        except asyncio.CancelledError:
            raise
        except Exception:
            yield {
                "type": "error",
                "code": "stream_failed",
                "message": "Agent execution failed. Please retry.",
            }
        finally:
            if not producer_task.done():
                producer_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, RuntimeError, OSError, ValueError):
                    await producer_task
```

### 3. `src/app/domain/ai/services/agent_service.py`
```python
"""High-level agent orchestration service coordinating sessions, runtime, and persistence."""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from app.domain.ai.runtime._context import CallContext
from app.domain.ai.runtime._loop import AgentRuntime
from app.domain.ai.runtime._spec import SpecTree
from app.domain.ai.runtime._store import OracleEventStore, OracleSessionStore
from app.domain.ai.runtime._stream import AgentStreamService


class AgentOrchestrationService:
    """Orchestrates dynamic agent sessions, persistence, and streaming turns."""

    def __init__(
        self,
        runtime: AgentRuntime,
        stream_service: AgentStreamService,
        spec_tree: SpecTree,
        session_store: OracleSessionStore,
        event_store: OracleEventStore,
    ) -> None:
        self._runtime = runtime
        self._stream_service = stream_service
        self._spec_tree = spec_tree
        self._session_store = session_store
        self._event_store = event_store

    async def stream_conversation_turn(
        self,
        *,
        session_id: str,
        user_id: str,
        message: str,
        services: Any = None,
        dynamic_context: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute a conversation turn and stream normalized SSE frames."""
        invocation_id = uuid4().hex
        existing_session = await self._session_store.get_session(session_id=session_id, user_id=user_id)
        if existing_session is None:
            await self._session_store.save_session(
                session_id=session_id,
                user_id=user_id,
                app_name="cymbal_coffee",
                state={},
            )

        history = await self._event_store.list_events(session_id=session_id)
        turn_num = len(history) // 2 + 1

        ctx = CallContext(
            session_id=session_id,
            invocation_id=invocation_id,
            turn=turn_num,
            state={},
            services=services,
        )

        event_generator = self._runtime.execute_turn(
            spec_tree=self._spec_tree,
            session_id=session_id,
            invocation_id=invocation_id,
            user_message=message,
            ctx=ctx,
            history=history,
            dynamic_context=dynamic_context,
        )

        async for frame in self._stream_service.adapt(event_generator, session_id=session_id):
            yield frame

    async def clear_session(self, session_id: str, user_id: str) -> None:
        """Clear session state and events."""
        await self._session_store.clear_session(session_id=session_id, user_id=user_id)
```

## Verification
- Strategy: `behavior_tdd`
- Initial Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/runtime/test_loop_stream.py`
  - Expected: Fails with `ModuleNotFoundError: No module named 'app.domain.ai.runtime._loop'`
- Final Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/runtime/test_loop_stream.py && make lint`
  - Expected: All unit tests pass, loop handles single and multi-turn tool calling, idle pings trigger on timeout, and `make lint` is clean.

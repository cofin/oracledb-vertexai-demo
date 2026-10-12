# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Terminal-aware Server-Sent Events (SSE) adapter with keep-alive pings."""

import asyncio
import contextlib
import time
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

import msgspec

from app.domain.ai.runtime._types import AgentEvent

__all__ = ("DEFAULT_PING_INTERVAL", "RESULT_PREVIEW_CHARS", "AgentStreamService", "build_tool_preview")

DEFAULT_PING_INTERVAL = 5.0
RESULT_PREVIEW_CHARS = 240


def build_tool_preview(response: dict[str, Any], max_chars: int = RESULT_PREVIEW_CHARS) -> tuple[str, str]:
    """Return status classification and bounded string preview for tool results.

    Args:
        response: Tool execution response dictionary.
        max_chars: Maximum character length for preview representation.

    Returns:
        Tuple containing status indicator and truncated string preview.
    """
    status = "error" if response.get("error") else "completed"
    encoded = msgspec.json.encode(response).decode("utf-8")
    if len(encoded) <= max_chars:
        return status, encoded
    return status, f"{encoded[: max_chars - 1]}…"


class AgentStreamService:
    """Adapts raw AgentEvents into an SSE-ready dictionary stream."""

    def __init__(self, ping_interval: float = DEFAULT_PING_INTERVAL) -> None:
        """Initialize stream adapter with keep-alive interval.

        Args:
            ping_interval: Seconds between idle keep-alive ping frames.
        """
        self._ping_interval = ping_interval

    async def adapt(
        self,
        event_stream: AsyncIterator[AgentEvent],
        session_id: str,
        *,
        final_metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Yield structured SSE event frames with keep-alive pings and guaranteed cleanup.

        Args:
            event_stream: Source async iterator of AgentEvent instances.
            session_id: Unique session identifier.
            final_metadata: Optional extra telemetry fields to merge into the final frame.

        Yields:
            Structured SSE event payload dictionaries.
        """
        fetch_next = asyncio.Event()
        fetch_next.set()
        queue: asyncio.Queue[AgentEvent | Exception | None] = asyncio.Queue(maxsize=1)
        producer_task = asyncio.create_task(self._producer(event_stream, queue, fetch_next))

        try:
            async for frame in self._drain_queue(queue, fetch_next, session_id, final_metadata=final_metadata):
                yield frame
        except asyncio.CancelledError:
            raise
        except Exception:
            yield {"type": "error", "code": "stream_failed", "message": "Agent execution failed. Please retry."}
        finally:
            if not producer_task.done():
                producer_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, RuntimeError, OSError, ValueError):
                    await producer_task

    async def _drain_queue(
        self,
        queue: asyncio.Queue[AgentEvent | Exception | None],
        fetch_next: asyncio.Event,
        session_id: str,
        *,
        final_metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Drain events from queue and yield formatted SSE frames.

        Args:
            queue: Internal event queue.
            fetch_next: Event notifying producer to fetch next event.
            session_id: Conversation session identifier.
            final_metadata: Optional extra telemetry fields to merge into the final frame.

        Yields:
            SSE formatted frame dictionaries.
        """
        start_time = time.perf_counter()
        yield {"type": "session", "session_id": session_id}

        seen_calls: set[str] = set()
        answer_parts: list[str] = []
        has_final = False
        usage_total = {"prompt_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cached_tokens": 0}

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

            for frame in _extract_frames_from_event(item, seen_calls, usage_total):
                if frame["type"] == "delta":
                    answer_parts.append(str(frame["text"]))
                yield frame

            if not item.partial and item.content and item.content.role == "model" and not item.function_calls():
                has_final = True
                if not answer_parts and (final_text := item.text()):
                    answer_parts.append(final_text)

            fetch_next.set()

        if has_final:
            yield _build_final_frame(
                session_id=session_id,
                answer_parts=answer_parts,
                start_time=start_time,
                usage_total=usage_total,
                final_metadata=final_metadata,
            )
        else:
            yield {
                "type": "error",
                "code": "stream_incomplete",
                "message": "Stream completed without final model turn.",
            }

    async def _producer(
        self,
        source: AsyncIterator[AgentEvent],
        queue: asyncio.Queue[AgentEvent | Exception | None],
        fetch_next: asyncio.Event,
    ) -> None:
        """Asynchronously pull events from source and feed into queue when requested.

        Args:
            source: Source event iterator.
            queue: Internal communication queue.
            fetch_next: Synchronization event signaling next item readiness.
        """
        try:
            await self._pump(source, queue, fetch_next)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            await queue.put(exc)

    async def _pump(
        self,
        source: AsyncIterator[AgentEvent],
        queue: asyncio.Queue[AgentEvent | Exception | None],
        fetch_next: asyncio.Event,
    ) -> None:
        """Inner pump loop fetching items and forwarding to queue."""
        while True:
            await fetch_next.wait()
            fetch_next.clear()
            try:
                item = await anext(source)
            except StopAsyncIteration:
                await queue.put(None)
                break
            await queue.put(item)


def _extract_frames_from_event(
    item: AgentEvent, seen_calls: set[str], usage_total: dict[str, int]
) -> list[dict[str, Any]]:
    """Extract tool and text delta frames from an incoming AgentEvent.

    Args:
        item: Ingested AgentEvent.
        seen_calls: Set of already emitted tool call IDs.
        usage_total: Running token count accumulator.

    Returns:
        List of generated SSE frame dictionaries.
    """
    frames: list[dict[str, Any]] = []

    if item.usage:
        usage_total["prompt_tokens"] += item.usage.prompt_tokens
        usage_total["output_tokens"] += item.usage.output_tokens
        usage_total["total_tokens"] += item.usage.total_tokens
        usage_total["cached_tokens"] += item.usage.cached_tokens

    for call in item.function_calls():
        call_key = call.id or call.name
        if call_key not in seen_calls:
            seen_calls.add(call_key)
            frames.append({
                "type": "tool_call",
                "id": call.id,
                "name": call.name,
                "author": item.agent,
                "args": call.args,
            })

    for resp in item.function_responses():
        status, preview = build_tool_preview(resp.response)
        frames.append({
            "type": "tool_end",
            "id": resp.id,
            "name": resp.name,
            "author": item.agent,
            "status": status,
            "result_preview": preview,
        })

    if not item.actions.get("aggregated"):
        text_chunk = item.text()
        if text_chunk and item.agent != "user":
            frames.append({"type": "delta", "text": text_chunk})

    return frames


def _build_final_frame(
    *,
    session_id: str,
    answer_parts: list[str],
    start_time: float,
    usage_total: dict[str, int],
    final_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the terminal final SSE frame matching the frontend stream contract.

    Args:
        session_id: Active conversation session identifier.
        answer_parts: Accumulated text delta chunks.
        start_time: Turn start timestamp from time.perf_counter().
        usage_total: Accumulated token usage metrics.
        final_metadata: Optional extra telemetry fields to merge into the payload.

    Returns:
        Dictionary representing the final SSE frame payload.
    """
    search_metrics: dict[str, Any] = {
        **usage_total,
        "similarity_scores": [],
        "avg_similarity": 0.0,
        "products_found": 0,
        "embedding_time_ms": 0.0,
        "vector_search_time_ms": 0.0,
    }
    final_payload: dict[str, Any] = {
        "type": "final",
        "answer": "".join(answer_parts),
        "session_id": session_id,
        "response_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
        "intent_detected": "GENERAL_CONVERSATION",
        "search_metrics": search_metrics,
        "from_cache": False,
        "embedding_cache_hit": False,
        "sql_phases": [],
        "store_results": [],
        "inventory_results": [],
        "map_actions": [],
        "location_context": None,
    }
    if not final_metadata:
        return final_payload
    if "search_metrics" in final_metadata and isinstance(final_metadata["search_metrics"], dict):
        merged_metrics = {**search_metrics, **final_metadata["search_metrics"]}
        final_payload.update(final_metadata)
        final_payload["search_metrics"] = merged_metrics
    else:
        final_payload.update(final_metadata)
    return final_payload

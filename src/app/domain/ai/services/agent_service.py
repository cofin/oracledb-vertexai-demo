# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""High-level agent orchestration service coordinating sessions, runtime, and persistence."""

from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, Literal
from uuid import uuid4

from app.domain.ai.runtime._context import CallContext
from app.domain.ai.runtime._loop import AgentRuntime
from app.domain.ai.runtime._spec import AgentSpec, GenerationConfig, SpecTree
from app.domain.ai.runtime._store import OracleEventStore, OracleSessionStore
from app.domain.ai.runtime._stream import AgentStreamService
from app.domain.ai.runtime._types import AgentEvent, Content, Part
from app.domain.chat.schemas import ChatMessage
from app.lib.settings import get_settings

__all__ = ("AgentOrchestrationService", "get_coffee_spec_tree")


def get_coffee_spec_tree() -> SpecTree:
    """Construct the coffee agent specification tree with coordinator and specialists.

    Returns:
        Configured SpecTree with coffee barista root coordinator.
    """
    settings = get_settings()
    model_name = settings.ai.chat_model

    coordinator = AgentSpec(
        name="coffee_barista",
        description="Friendly, knowledgeable Cymbal Coffee barista guiding recommendations and recipes.",
        model=model_name,
        static_instruction=(
            "You are the Cymbal Coffee Barista, an expert AI assistant guiding customers to their "
            "ideal specialty roasts, brewing techniques, and store availability. You are helpful, "
            "knowledgeable, and grounded in the coffee catalog."
        ),
        generation=GenerationConfig(temperature=0.2, max_output_tokens=4096),
    )
    return SpecTree(root=coordinator)


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
        """Initialize the orchestration service with runtime and persistence stores.

        Args:
            runtime: Core re-entrant agent execution loop.
            stream_service: SSE stream frame adapter.
            spec_tree: Hierarchical agent specification tree.
            session_store: Oracle session state store.
            event_store: Oracle conversation event log store.
        """
        self._runtime = runtime
        self._stream_service = stream_service
        self._spec_tree = spec_tree
        self._session_store = session_store
        self._event_store = event_store

    async def stream_conversation_turn(
        self, *, session_id: str, user_id: str, message: str, services: Any = None, dynamic_context: str | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute a conversation turn and stream normalized SSE frames.

        Args:
            session_id: Conversation session identifier.
            user_id: Authenticated or anonymous user identifier.
            message: User prompt text.
            services: Request-scoped service container for tool dispatch.
            dynamic_context: Optional dynamic runtime context.

        Yields:
            Normalized SSE frame dictionaries for frontend consumers.
        """
        invocation_id = uuid4().hex
        existing_session = await self._session_store.get_session(session_id=session_id, user_id=user_id)
        if existing_session is None:
            await self._session_store.save_session(
                session_id=session_id, user_id=user_id, app_name="cymbal_coffee", state={}
            )

        history = await self._event_store.list_events(session_id=session_id)
        turn_num = len(history) // 2 + 1

        ctx = CallContext(
            session_id=session_id, invocation_id=invocation_id, turn=turn_num, state={}, services=services
        )

        user_event = AgentEvent(
            session_id=session_id,
            invocation_id=invocation_id,
            agent="user",
            turn=turn_num,
            content=Content(role="user", parts=[Part(text=message)]),
        )
        await self._event_store.append_event(user_event)

        raw_stream = self._runtime.execute_turn(
            spec_tree=self._spec_tree,
            session_id=session_id,
            invocation_id=invocation_id,
            user_message=message,
            ctx=ctx,
            history=history,
            dynamic_context=dynamic_context,
        )

        async def _persisting_stream() -> AsyncIterator[AgentEvent]:
            async for event in raw_stream:
                if not event.partial and event.content:
                    await self._event_store.append_event(event)
                yield event

        async for frame in self._stream_service.adapt(_persisting_stream(), session_id=session_id):
            yield frame

    async def get_display_history(self, session_id: str, user_id: str) -> list[ChatMessage]:
        """Retrieve recent conversation history formatted for HTML display templates.

        Args:
            session_id: Conversation session identifier.
            user_id: Authenticated or anonymous user identifier.

        Returns:
            List of ChatMessage objects formatted for templates.
        """
        del user_id
        events = await self._event_store.list_events(session_id=session_id)
        display_messages: list[ChatMessage] = []
        for event in events:
            if not event.content:
                continue
            source: Literal["human", "ai"] = "human" if event.agent == "user" else "ai"
            text_parts = [p.text for p in event.content.parts if p.text]
            if text_parts:
                display_messages.append(ChatMessage(message="".join(text_parts), source=source))
        return display_messages

    async def clear_session(self, session_id: str, user_id: str) -> None:
        """Clear session state and associated event rows.

        Args:
            session_id: Conversation session identifier.
            user_id: Authenticated or anonymous user identifier.
        """
        await self._session_store.clear_session(session_id=session_id, user_id=user_id)

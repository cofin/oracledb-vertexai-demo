# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A2A AgentExecutor implementation delegating to AgentOrchestrationService."""

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role
from dishka import AsyncContainer, Scope

from app.domain.ai.services.agent_service import AgentOrchestrationService


class CoffeeAgentExecutor(AgentExecutor):
    """Executes incoming A2A turns within a request-scoped Dishka container."""

    def __init__(self, container: AsyncContainer | None = None) -> None:
        """Initialize the CoffeeAgentExecutor with an optional root Dishka container.

        Args:
            container: The root application-level Dishka container, if already built.
        """
        self._container = container

    def _resolve_container(self, context: RequestContext) -> AsyncContainer:
        """Resolve the active root Dishka container from context state or lazy factory.

        Args:
            context: The A2A request context containing server call state.

        Returns:
            The root AsyncContainer instance.
        """
        if self._container is not None:
            container: AsyncContainer = self._container
            visited_containers: set[int] = {id(container)}
            while container.parent_container is not None:
                parent = container.parent_container
                if id(parent) in visited_containers:
                    break
                visited_containers.add(id(parent))
                container = parent
            return container

        call_ctx = getattr(context, "call_context", None)
        if call_ctx is not None and hasattr(call_ctx, "state") and isinstance(call_ctx.state, dict):
            litestar_state = call_ctx.state.get("litestar_state", {})
            if isinstance(litestar_state, dict):
                app_container = litestar_state.get("dishka_container")
                if isinstance(app_container, AsyncContainer):
                    current: AsyncContainer = app_container
                    visited_app: set[int] = {id(current)}
                    while current.parent_container is not None:
                        parent_app = current.parent_container
                        if id(parent_app) in visited_app:
                            break
                        visited_app.add(id(parent_app))
                        current = parent_app
                    return current

        from app.ioc import make_container
        from app.lib.di import LitestarProvider

        new_container = make_container(LitestarProvider())
        self._container = new_container
        return new_container

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Process an incoming A2A message and push responses to event_queue.

        Args:
            context: Request context containing user message and task identity.
            event_queue: Event queue for publishing responses and stream events.
        """
        user_text = ""
        if hasattr(context, "get_user_input"):
            user_text = context.get_user_input()
        if not user_text and context.message and context.message.parts:
            for part in context.message.parts:
                part_text = getattr(part, "text", "")
                if part_text:
                    user_text += part_text

        session_id = context.context_id or "a2a-default-session"
        user_id = "a2a-client"
        if hasattr(context, "call_context") and context.call_context is not None:
            user_val = getattr(context.call_context, "user", None)
            if user_val:
                user_id = str(user_val)

        container = self._resolve_container(context)
        async with container(scope=Scope.REQUEST) as req_container:
            orchestrator = await req_container.get(AgentOrchestrationService)
            accumulated_answer: list[str] = []

            async for frame in orchestrator.stream_conversation_turn(
                session_id=session_id, user_id=user_id, message=user_text
            ):
                if frame.get("type") == "delta":
                    delta_text = str(frame.get("text", ""))
                    accumulated_answer.append(delta_text)

            complete_message = Message(role=Role.ROLE_AGENT, parts=[Part(text="".join(accumulated_answer))])
            await event_queue.enqueue_event(complete_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel an in-flight A2A task.

        Args:
            context: Request context for the task to cancel.
            event_queue: Event queue for sending cancellation confirmation.
        """
        del context, event_queue


__all__ = ("CoffeeAgentExecutor",)

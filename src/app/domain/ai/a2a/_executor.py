# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A2A AgentExecutor implementation delegating to AgentOrchestrationService."""

from typing import Any

from a2a.auth.user import User
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.context import ServerCallContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part
from dishka import AsyncContainer, Scope

from app.domain.ai.services._agent import AgentOrchestrationService

__all__ = ("ANONYMOUS_A2A_USER", "CoffeeAgentExecutor", "build_a2a_call_context", "resolve_a2a_user_id")

ANONYMOUS_A2A_USER = "anonymous"


def resolve_a2a_user_id(user_obj: Any) -> str:
    """Resolve a deterministic user identifier string for A2A task ownership.

    Args:
        user_obj: Raw user value from ASGI scope or ServerCallContext.

    Returns:
        Stable user identifier string, defaulting to 'anonymous'.
    """
    if user_obj is None:
        return ANONYMOUS_A2A_USER
    if isinstance(user_obj, str):
        stripped = user_obj.strip()
        return stripped if stripped and not stripped.startswith("<") else ANONYMOUS_A2A_USER
    if isinstance(user_obj, User):
        name = user_obj.user_name.strip()
        if name:
            return name
        wrapped = getattr(user_obj, "value", None)
        return resolve_a2a_user_id(wrapped) if wrapped is not None and wrapped is not user_obj else ANONYMOUS_A2A_USER

    is_auth = (
        user_obj.get("is_authenticated") if isinstance(user_obj, dict) else getattr(user_obj, "is_authenticated", None)
    )
    if is_auth is False:
        return ANONYMOUS_A2A_USER

    resolved = ANONYMOUS_A2A_USER
    for attr in ("id", "sub", "username", "user_name"):
        val = user_obj.get(attr) if isinstance(user_obj, dict) else getattr(user_obj, attr, None)
        if val is not None and str(val).strip():
            resolved = str(val).strip()
            break
    return resolved


def build_a2a_call_context(request: Any, context: ServerCallContext | None = None) -> ServerCallContext:
    """Build a ServerCallContext with deterministic task owner and Dishka container state.

    Args:
        request: Incoming Litestar Request instance.
        context: Optional base ServerCallContext constructed by the transport.

    Returns:
        Enriched ServerCallContext with deterministic user scope and session metadata.
    """
    scope = getattr(request, "scope", {}) or {}
    raw_headers = getattr(request, "headers", {}) or {}
    headers = {str(k).lower(): str(v) for k, v in dict(raw_headers).items()}
    litestar_state = scope.get("state", {}) if isinstance(scope, dict) else {}

    dishka_container = litestar_state.get("dishka_container") if isinstance(litestar_state, dict) else None
    if dishka_container is None:
        app_obj = scope.get("app") if isinstance(scope, dict) else getattr(request, "app", None)
        app_state = getattr(app_obj, "state", None)
        if app_state is not None:
            dishka_container = getattr(app_state, "dishka_container", None)

    user_id = resolve_a2a_user_id(scope.get("user") if isinstance(scope, dict) else None)
    session_id = headers.get("x-session-id")

    merged_state: dict[str, Any] = (
        dict(context.state) if context is not None and isinstance(context.state, dict) else {}
    )
    merged_state.update({
        "auth": scope.get("auth") if isinstance(scope, dict) else None,
        "headers": headers,
        "litestar_state": litestar_state,
        "user_id": user_id,
        "session_id": session_id,
        "dishka_container": dishka_container,
    })
    requested_extensions = context.requested_extensions if context is not None else set()
    return ServerCallContext(
        state=merged_state,
        user=_A2AUser(user_id=user_id, authenticated=user_id != ANONYMOUS_A2A_USER),
        requested_extensions=requested_extensions,
    )


class CoffeeAgentExecutor(AgentExecutor):
    """Executes incoming A2A turns within a request-scoped Dishka container."""

    def __init__(self, container: AsyncContainer | None = None) -> None:
        """Initialize the CoffeeAgentExecutor with an optional root Dishka container.

        Args:
            container: The root application-level Dishka container, if already built.
        """
        self._container = container

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Process an incoming A2A message and publish task lifecycle events to event_queue.

        Args:
            context: Request context containing user message and task identity.
            event_queue: Event queue for publishing responses and stream events.
        """
        container = self._resolve_container(context)
        user_text = self._extract_user_text(context)
        session_id = self._resolve_session_id(context)
        user_id = self._resolve_user_id(context)
        task_id = context.task_id or "a2a-task"
        updater = TaskUpdater(event_queue=event_queue, task_id=task_id, context_id=session_id)

        await updater.start_work()
        try:
            await self._run_turn_and_publish(
                container=container, session_id=session_id, user_id=user_id, user_text=user_text, updater=updater
            )
        except Exception as exc:
            err_msg = updater.new_agent_message(parts=[Part(text=f"Agent execution failed ({type(exc).__name__}).")])
            await updater.failed(message=err_msg)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel an in-flight A2A task.

        Args:
            context: Request context for the task to cancel.
            event_queue: Event queue for sending cancellation confirmation.
        """
        task_id = context.task_id or "a2a-task"
        session_id = self._resolve_session_id(context)
        updater = TaskUpdater(event_queue=event_queue, task_id=task_id, context_id=session_id)
        await updater.cancel()

    async def _run_turn_and_publish(
        self, *, container: AsyncContainer, session_id: str, user_id: str, user_text: str, updater: TaskUpdater
    ) -> None:
        """Run one orchestrated turn inside a REQUEST scope and publish artifacts to TaskUpdater."""
        async with container(scope=Scope.REQUEST) as req_container:
            orchestrator = await req_container.get(AgentOrchestrationService)
            accumulated_answer: list[str] = []
            final_answer = ""
            async for frame in orchestrator.stream_conversation_turn(
                session_id=session_id, user_id=user_id, message=user_text, services=req_container
            ):
                frame_type = frame.get("type")
                if frame_type == "error":
                    raise RuntimeError(str(frame.get("message") or "Agent stream execution failed."))
                if frame_type == "delta":
                    accumulated_answer.append(str(frame.get("text", "")))
                elif frame_type == "final":
                    final_answer = str(frame.get("answer") or "")
            answer_text = "".join(accumulated_answer) or final_answer
            if answer_text:
                await updater.add_artifact(parts=[Part(text=answer_text)], name="response")
            agent_msg = updater.new_agent_message(parts=[Part(text=answer_text)])
            await updater.complete(message=agent_msg)

    def _resolve_container(self, context: RequestContext) -> AsyncContainer:
        """Resolve the root Dishka container from instance or call_context state.

        Args:
            context: The A2A request context containing server call state.

        Returns:
            The root AsyncContainer instance.

        Raises:
            RuntimeError: If no Dishka AsyncContainer is available.
        """
        if self._container is not None:
            return _unwrap_root_container(self._container)

        call_ctx = getattr(context, "call_context", None)
        state = getattr(call_ctx, "state", None)
        if isinstance(state, dict):
            direct = state.get("dishka_container")
            if isinstance(direct, AsyncContainer):
                return _unwrap_root_container(direct)
            litestar_state = state.get("litestar_state")
            if isinstance(litestar_state, dict):
                nested = litestar_state.get("dishka_container")
                if isinstance(nested, AsyncContainer):
                    return _unwrap_root_container(nested)

        msg = "Dishka AsyncContainer is not available in A2A RequestContext."
        raise RuntimeError(msg)

    def _extract_user_text(self, context: RequestContext) -> str:
        """Extract user input text from an A2A RequestContext."""
        if hasattr(context, "get_user_input"):
            text = context.get_user_input()
            if text:
                return str(text)
        if context.message and context.message.parts:
            return "".join(getattr(part, "text", "") for part in context.message.parts if getattr(part, "text", ""))
        return ""

    def _resolve_session_id(self, context: RequestContext) -> str:
        """Resolve session identifier preferring X-Session-ID header over context_id."""
        call_ctx = getattr(context, "call_context", None)
        state = getattr(call_ctx, "state", None)
        if isinstance(state, dict):
            explicit = state.get("session_id")
            if isinstance(explicit, str) and explicit.strip():
                return explicit.strip()
            headers = state.get("headers")
            if isinstance(headers, dict):
                header_val = headers.get("x-session-id")
                if isinstance(header_val, str) and header_val.strip():
                    return header_val.strip()
        return context.context_id or "a2a-default-session"

    def _resolve_user_id(self, context: RequestContext) -> str:
        """Resolve deterministic user identifier from call_context state or user."""
        call_ctx = getattr(context, "call_context", None)
        if call_ctx is None:
            return ANONYMOUS_A2A_USER
        state = getattr(call_ctx, "state", None)
        if isinstance(state, dict):
            explicit = state.get("user_id")
            if isinstance(explicit, str) and explicit.strip():
                return explicit.strip()
        return resolve_a2a_user_id(getattr(call_ctx, "user", None))


class _A2AUser(User):
    """Deterministic A2A User wrapper for task store ownership scoping."""

    def __init__(self, user_id: str, *, authenticated: bool = False) -> None:
        self._user_id = user_id or ANONYMOUS_A2A_USER
        self._authenticated = authenticated

    @property
    def is_authenticated(self) -> bool:
        """Whether the caller is authenticated."""
        return self._authenticated

    @property
    def user_name(self) -> str:
        """Deterministic owner identifier."""
        return self._user_id

    def __str__(self) -> str:
        """Return the deterministic owner identifier string."""
        return self._user_id


def _unwrap_root_container(container: AsyncContainer) -> AsyncContainer:
    """Walk parent_container links to return the root APP-scoped AsyncContainer."""
    current = container
    visited: set[int] = {id(current)}
    while current.parent_container is not None:
        parent = current.parent_container
        if id(parent) in visited:
            break
        visited.add(id(parent))
        current = parent
    return current
